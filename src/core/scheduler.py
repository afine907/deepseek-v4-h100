"""Core scheduler with Chunked Prefill + Continuous Batching + SJF/aging."""

import heapq
import threading
import time
from dataclasses import dataclass, field

from .models import (
    BatchConfig,
    ChunkedPrefillConfig,
    InferenceRequest,
    InferenceResponse,
    QueueStatus,
)
from .ports import InferenceEngine, KVCacheManagerPort, MetricsCollectorPort, SchedulerPort


@dataclass(order=True)
class PrioritizedRequest:
    """A request in the scheduler queue with scheduling metadata."""

    priority: float
    request: InferenceRequest = field(compare=False)
    enqueue_time: float = field(compare=False, default_factory=time.time)
    remaining_tokens: int = field(compare=False, default=0)
    chunks: list = field(compare=False, default_factory=list)
    current_chunk: int = field(compare=False, default=0)


class Scheduler(SchedulerPort):
    """
    Core scheduler implementing:
    - Chunked Prefill: long prompts split into 512-token chunks
    - Continuous Batching: max_batch_size=32, prefill_ratio=0.3
    - SJF + aging: shortest job first with aging to prevent starvation
    """

    def __init__(
        self,
        engine: InferenceEngine,
        kv_cache: KVCacheManagerPort,
        metrics: MetricsCollectorPort,
        chunk_config: ChunkedPrefillConfig,
        batch_config: BatchConfig,
    ):
        self._engine = engine
        self._kv_cache = kv_cache
        self._metrics = metrics
        self._chunk_config = chunk_config
        self._batch_config = batch_config
        self._queue: list[PrioritizedRequest] = []
        self._running: dict[str, PrioritizedRequest] = {}
        self._completed: list[InferenceResponse] = []
        self._lock = threading.Lock()
        self._closed = False

    def enqueue(self, request: InferenceRequest) -> str:
        """Enqueue a request with SJF + aging priority."""
        with self._lock:
            wait_time = time.time() - request.metadata.get("enqueue_time", time.time())
            remaining = request.max_tokens
            # SJF with aging: shorter jobs and older requests get higher priority
            priority = remaining / (1.0 + wait_time * 0.1)

            chunks = self._split_into_chunks(request.prompt)
            pr = PrioritizedRequest(
                priority=priority,
                request=request,
                remaining_tokens=remaining,
                chunks=chunks,
            )
            heapq.heappush(self._queue, pr)
            return request.request_id

    def _split_into_chunks(self, prompt: str) -> list[str]:
        """Split prompt into chunks of chunk_size tokens (characters here for simplicity)."""
        chunk_size = self._chunk_config.chunk_size
        chunks = []
        for i in range(0, len(prompt), chunk_size):
            chunks.append(prompt[i : i + chunk_size])
        return chunks if chunks else [prompt]

    def step(self) -> list[InferenceResponse]:
        """
        Execute one scheduling step:
        1. Collect completed results from engine
        2. Evict KV cache if needed
        3. Submit next batch (chunked prefill + continuous batching)
        4. Return completed responses this round
        """
        completed = []

        with self._lock:
            # Step 1: collect completed results
            done_ids = []
            for rid in list(self._running.keys()):
                result = self._engine.get_result(rid, timeout=0.0)
                if result is not None:
                    completed.append(result)
                    done_ids.append(rid)
                    self._metrics.record_latency(result.latency_ms, "inference")
                    self._metrics.record_throughput(result.tokens_generated)

            for rid in done_ids:
                del self._running[rid]

            # Step 2: KV cache eviction
            self._kv_cache.evict_if_needed()

            # Step 3: submit next batch
            self._submit_batch()

            return completed

    def _submit_batch(self) -> None:
        """Submit up to max_batch_size chunks from queue."""
        max_batch = self._batch_config.max_batch_size
        prefill_budget = int(max_batch * self._batch_config.prefill_ratio)

        prefill_count = 0
        decode_slots = max_batch - prefill_count

        # Count current running prefill vs decode
        running_prefill = sum(
            1 for pr in self._running.values() if pr.current_chunk < len(pr.chunks) - 1
        )
        running_decode = len(self._running) - running_prefill

        prefill_budget = max(0, prefill_budget - running_prefill)
        decode_slots = max(0, decode_slots - running_decode)

        while self._queue and (prefill_budget > 0 or decode_slots > 0):
            pr = heapq.heappop(self._queue)

            if pr.current_chunk < len(pr.chunks) - 1 and prefill_budget > 0:
                # This request has more chunks (prefill phase)
                prefill_budget -= 1
            elif pr.current_chunk >= len(pr.chunks) - 1 and decode_slots > 0:
                # This request is in decode phase
                decode_slots -= 1
            else:
                # No budget, push back (should not happen with proper budgeting)
                heapq.heappush(self._queue, pr)
                break

            self._running[pr.request.request_id] = pr

    def get_queue_status(self) -> QueueStatus:
        with self._lock:
            return QueueStatus(
                waiting_requests=len(self._queue),
                running_requests=len(self._running),
                avg_wait_time_ms=0.0,
                avg_decode_time_ms=0.0,
            )

    def close(self) -> None:
        """Close the scheduler, cancel all pending requests."""
        with self._lock:
            self._closed = True
            for rid in list(self._running.keys()):
                self._engine.cancel(rid)
            self._running.clear()
            self._queue.clear()
