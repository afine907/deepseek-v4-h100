"""Mock adapters for testing and CI (no vLLM dependency)."""

import random
import threading
import time
from collections import OrderedDict

from ..core.models import (
    EngineStatus,
    FinishReason,
    InferenceRequest,
    InferenceResponse,
)
from ..core.ports import InferenceEngine, KVCacheManagerPort, MetricsCollectorPort


class MockInferenceEngine(InferenceEngine):
    """Mock inference engine that does not depend on vLLM. For testing and CI.

    Uses a background thread to model async latency — matches VLLMAdapter's pattern.
    """

    def __init__(
        self,
        mean_latency_ms: float = 500.0,
        std_latency_ms: float = 200.0,
        mock_hit_rate: float = 0.4,
    ):
        self._mean = mean_latency_ms / 1000.0
        self._std = std_latency_ms / 1000.0
        self._mock_hit_rate = mock_hit_rate
        self._requests: dict[str, tuple[InferenceRequest, float]] = {}
        self._completed: dict[str, InferenceResponse] = {}
        self._lock = threading.Lock()
        self._id_counter = 0
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._poll_results, daemon=True)
        self._thread.start()

    def _poll_results(self) -> None:
        """Background thread: complete requests after modeled latency."""
        while not self._stop_event.is_set():
            with self._lock:
                to_complete = [
                    rid for rid, (_, start) in self._requests.items() if rid not in self._completed
                    and (time.time() - start) >= self._mean
                ]
                for rid in to_complete:
                    request, _ = self._requests[rid]
                    latency_ms = max(50.0, random.gauss(self._mean * 1000, self._std * 1000))
                    tokens = random.randint(20, 200)
                    self._completed[rid] = InferenceResponse(
                        request_id=rid,
                        generated_text=f"Mock response for: {request.prompt[:50]}...",
                        finish_reason=FinishReason.STOP,
                        latency_ms=latency_ms,
                        tokens_generated=tokens,
                    )
            self._stop_event.wait(0.01)  # poll every 10ms

    def submit(self, request: InferenceRequest) -> str:
        with self._lock:
            rid = request.request_id or f"mock-{self._id_counter}"
            self._id_counter += 1
            self._requests[rid] = (request, time.time())
        return rid

    def get_result(self, request_id: str, timeout: float = 30.0) -> InferenceResponse | None:
        deadline = time.time() + timeout
        while True:
            with self._lock:
                if request_id in self._completed:
                    return self._completed.pop(request_id)
                if request_id not in self._requests:
                    return None
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            # Wait for result to become available (will be checked in next iteration)
            time.sleep(min(0.05, remaining))

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            self._completed.pop(request_id, None)
            return self._requests.pop(request_id, None) is not None

    def get_status(self) -> EngineStatus:
        return EngineStatus(
            ready=True,
            model_loaded=True,
            device="mock",
            max_batch_size=32,
        )

    def __del__(self):
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=1.0)


class MockKVCacheManager(KVCacheManagerPort):
    """Mock LRU KV Cache Manager for testing."""

    def __init__(
        self,
        capacity_blocks: int = 1000,
        high_watermark: float = 0.90,
        low_watermark: float = 0.75,
    ):
        self._capacity = capacity_blocks
        self._high = high_watermark
        self._low = low_watermark
        self._blocks: OrderedDict[str, float] = OrderedDict()
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._lock = threading.Lock()
        self._current_usage = 0.0

    def _evict_locked(self) -> int:
        """Evict blocks while caller holds self._lock. Returns evicted count."""
        if self._current_usage / max(self._capacity, 1) < self._high:
            return 0
        evicted = 0
        while self._current_usage > self._capacity * self._low and len(self._blocks) > 0:
            oldest = next(iter(self._blocks))
            del self._blocks[oldest]
            self._current_usage -= 1
            self._eviction_count += 1
            evicted += 1
        return evicted

    def evict_if_needed(self) -> int:
        with self._lock:
            return self._evict_locked()

    def record_access(self, block_id: str) -> None:
        with self._lock:
            if block_id in self._blocks:
                self._blocks.move_to_end(block_id)
                self._hit_count += 1
            else:
                self._blocks[block_id] = time.time()
                self._current_usage += 1
                self._miss_count += 1
                self._evict_locked()

    def get_hit_rate(self) -> float:
        with self._lock:
            total = self._hit_count + self._miss_count
            return self._hit_count / total if total > 0 else 0.0


class MockMetricsCollector(MetricsCollectorPort):
    """Mock metrics collector for testing."""

    def __init__(self):
        self._latencies: list[float] = []
        self._tokens: list[int] = []
        self._lock = threading.Lock()

    def record_latency(self, latency_ms: float, stage: str = "inference") -> None:
        with self._lock:
            self._latencies.append(latency_ms)

    def record_throughput(self, tokens: int) -> None:
        with self._lock:
            self._tokens.append(tokens)

    def get_metrics(self) -> dict:
        with self._lock:
            lat = self._latencies[-100:] if len(self._latencies) > 100 else list(self._latencies)
            sorted_lat = sorted(lat)
            p50 = sorted_lat[len(sorted_lat) // 2] if sorted_lat else 0
            p99 = sorted_lat[int(len(sorted_lat) * 0.99)] if sorted_lat else 0
            return {
                "inference_latency_ms_p50": p50,
                "inference_latency_ms_p99": p99,
                "tokens_total": sum(self._tokens),
                "requests_total": len(self._latencies),
            }
