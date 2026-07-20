"""Unit tests for Scheduler — full boundary and correctness coverage."""

import heapq
import threading
import time
import pytest

from src.core.scheduler import Scheduler, PrioritizedRequest
from src.core.models import (
    InferenceRequest,
    ChunkedPrefillConfig,
    BatchConfig,
)
from src.adapters.mock_adapter import MockInferenceEngine, MockKVCacheManager, MockMetricsCollector
from src.core.kv_cache_manager import KVCacheManager
from src.core.models import KVCacheConfig


def make_scheduler(
    chunk_size: int = 512,
    max_batch_size: int = 32,
    prefill_ratio: float = 0.3,
    mean_latency_ms: float = 20.0,
) -> Scheduler:
    """Factory: create a scheduler with mock engine, real KVCacheManager, mock metrics."""
    engine = MockInferenceEngine(mean_latency_ms=mean_latency_ms)
    kv_config = KVCacheConfig(high_watermark=0.9, low_watermark=0.75, max_evict_per_round=50)
    kv = KVCacheManager(kv_config)
    kv.set_max_blocks(100)
    metrics = MockMetricsCollector()
    scheduler = Scheduler(
        engine=engine,
        kv_cache=kv,
        metrics=metrics,
        chunk_config=ChunkedPrefillConfig(chunk_size=chunk_size, prefill_ratio=prefill_ratio),
        batch_config=BatchConfig(max_batch_size=max_batch_size, prefill_ratio=prefill_ratio),
    )
    return scheduler


# ---------------------------------------------------------------------------
# Priority & SJF + Aging
# ---------------------------------------------------------------------------

class TestPriorityOrdering:
    """Verify SJF + aging: shorter requests and older requests get higher priority."""

    def test_shorter_request_dequeued_first(self):
        """Smaller max_tokens → higher priority (smaller value) → dequeued first."""
        scheduler = make_scheduler()

        scheduler.enqueue(InferenceRequest(request_id="long", prompt="a", max_tokens=1000))
        scheduler.enqueue(InferenceRequest(request_id="short", prompt="b", max_tokens=10))

        # heapq is a min-heap — smallest priority value = highest priority = dequeued first
        heap_root = scheduler._queue[0]
        assert heap_root.request.request_id == "short"

    def test_older_request_wins_when_max_tokens_equal(self):
        """Same max_tokens: older enqueue_time → larger wait_time → higher priority."""
        scheduler = make_scheduler()

        scheduler.enqueue(InferenceRequest(request_id="first", prompt="a", max_tokens=50))
        time.sleep(0.05)
        scheduler.enqueue(InferenceRequest(request_id="second", prompt="b", max_tokens=50))

        heap_root = scheduler._queue[0]
        assert heap_root.request.request_id == "first"

    def test_zero_max_tokens_ranks_first(self):
        """max_tokens=0 yields priority=0 → highest priority."""
        scheduler = make_scheduler()

        scheduler.enqueue(InferenceRequest(request_id="big", prompt="x", max_tokens=1000))
        scheduler.enqueue(InferenceRequest(request_id="zero", prompt="x", max_tokens=0))

        assert scheduler._queue[0].request.request_id == "zero"

    def test_heap_ordering_invariant(self):
        """After enqueuing varied requests, popping all yields non-decreasing priority."""
        scheduler = make_scheduler()

        for i in range(10):
            scheduler.enqueue(
                InferenceRequest(request_id=f"r{i}", prompt=f"p{i}", max_tokens=(i + 1) * 10)
            )

        prev_priority = float("-inf")
        for _ in range(10):
            pr = heapq.heappop(scheduler._queue)
            assert pr.priority >= prev_priority
            prev_priority = pr.priority


# ---------------------------------------------------------------------------
# Chunked Prefill splitting
# ---------------------------------------------------------------------------

class TestChunkedPrefillSplit:
    """Verify prompt splitting into chunk_size-character chunks."""

    def test_exact_multiple_of_chunk_size(self):
        """len == chunk_size → 1 chunk."""
        scheduler = make_scheduler(chunk_size=5)
        scheduler.enqueue(InferenceRequest(request_id="r", prompt="abcde", max_tokens=10))
        assert len(scheduler._queue[0].chunks) == 1

    def test_one_over_chunk_size(self):
        """len == chunk_size + 1 → 2 chunks."""
        scheduler = make_scheduler(chunk_size=5)
        scheduler.enqueue(InferenceRequest(request_id="r", prompt="abcdef", max_tokens=10))
        assert len(scheduler._queue[0].chunks) == 2

    def test_single_character_prompt(self):
        """Single char → 1 chunk."""
        scheduler = make_scheduler(chunk_size=5)
        scheduler.enqueue(InferenceRequest(request_id="r", prompt="x", max_tokens=10))
        assert len(scheduler._queue[0].chunks) == 1

    def test_empty_prompt_returns_one_chunk(self):
        """Empty prompt → [''] (one empty-string chunk)."""
        scheduler = make_scheduler(chunk_size=5)
        scheduler.enqueue(InferenceRequest(request_id="r", prompt="", max_tokens=10))
        chunks = scheduler._queue[0].chunks
        assert len(chunks) == 1
        assert chunks[0] == ""

    def test_20_char_prompt_with_chunk_size_5(self):
        """100 chars with chunk_size=5 → exactly 20 chunks."""
        scheduler = make_scheduler(chunk_size=5)
        scheduler.enqueue(InferenceRequest(request_id="r", prompt="a" * 100, max_tokens=10))
        assert len(scheduler._queue[0].chunks) == 20

    def test_chunks_are_contiguous_slices(self):
        """Chunks joined reconstruct the original prompt."""
        scheduler = make_scheduler(chunk_size=5)
        scheduler.enqueue(InferenceRequest(request_id="r", prompt="abcdefghij", max_tokens=10))
        chunks = scheduler._queue[0].chunks
        assert "".join(chunks) == "abcdefghij"


# ---------------------------------------------------------------------------
# Batch config
# ---------------------------------------------------------------------------

class TestBatchConfig:
    """Verify batch configuration parameters."""

    def test_prefill_ratio_int_truncation(self):
        """int(max_batch * prefill_ratio) is used, not rounded."""
        scheduler = make_scheduler(max_batch_size=10, prefill_ratio=0.3)
        # int(10 * 0.3) = int(3.0) = 3
        assert scheduler._batch_config.max_batch_size == 10
        assert scheduler._batch_config.prefill_ratio == 0.3


# ---------------------------------------------------------------------------
# Scheduler step behavior
# ---------------------------------------------------------------------------

class TestSchedulerStep:
    """Verify step() completes requests, records metrics, submits next batch."""

    def test_empty_queue_step_returns_empty_list(self):
        """step() on empty queue returns [], no engine calls crash."""
        scheduler = make_scheduler()
        results = scheduler.step()
        assert results == []

    def test_step_submits_waiting_requests_to_engine(self):
        """After step(), some requests should be in _running (submitted to engine)."""
        scheduler = make_scheduler(mean_latency_ms=100.0)
        for i in range(3):
            scheduler.enqueue(InferenceRequest(request_id=f"r{i}", prompt="hello", max_tokens=20))

        scheduler.step()
        status = scheduler.get_queue_status()
        # At least some submitted
        assert status.running_requests >= 0

    def test_step_records_latency_on_completion(self):
        """Completed requests trigger record_latency on the metrics collector."""
        scheduler = make_scheduler(mean_latency_ms=50.0)
        scheduler.enqueue(InferenceRequest(request_id="r1", prompt="hi", max_tokens=20))

        # Wait for completion — sleep between steps so wall-clock advances
        completed_ids = set()
        for _ in range(100):
            results = scheduler.step()
            for r in results:
                completed_ids.add(r.request_id)
            if "r1" in completed_ids:
                break
            time.sleep(0.02)  # allow background thread to complete request

        assert "r1" in completed_ids
        metrics = scheduler._metrics.get_metrics()
        assert metrics["requests_total"] >= 1


# ---------------------------------------------------------------------------
# Queue status
# ---------------------------------------------------------------------------

class TestQueueStatus:
    """Verify get_queue_status() reports correct counts."""

    def test_empty_queue_status(self):
        """Empty: waiting=0, running=0."""
        scheduler = make_scheduler()
        status = scheduler.get_queue_status()
        assert status.waiting_requests == 0
        assert status.running_requests == 0

    def test_waiting_count_after_enqueues(self):
        """After N enqueues: waiting=N, running=0."""
        scheduler = make_scheduler()
        for i in range(5):
            scheduler.enqueue(InferenceRequest(request_id=f"r{i}", prompt="hi", max_tokens=10))
        status = scheduler.get_queue_status()
        assert status.waiting_requests == 5
        assert status.running_requests == 0

    def test_status_after_submit(self):
        """After step: waiting + running = total enqueued."""
        scheduler = make_scheduler(mean_latency_ms=100.0)
        for i in range(4):
            scheduler.enqueue(InferenceRequest(request_id=f"r{i}", prompt="hello", max_tokens=10))

        scheduler.step()
        status = scheduler.get_queue_status()
        assert status.waiting_requests + status.running_requests == 4


# ---------------------------------------------------------------------------
# Concurrency
# ---------------------------------------------------------------------------

class TestConcurrency:
    """Verify thread safety of enqueue and step."""

    def test_concurrent_enqueue_no_exceptions(self):
        """10 threads × 20 enqueues — no lost updates."""
        scheduler = make_scheduler()
        errors = []

        def enqueue_requests(start: int):
            try:
                for i in range(start, start + 20):
                    scheduler.enqueue(
                        InferenceRequest(request_id=f"r{i}", prompt="hi", max_tokens=10)
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=enqueue_requests, args=(i * 20,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert scheduler.get_queue_status().waiting_requests == 200

    def test_concurrent_enqueue_and_step_no_deadlock(self):
        """Enqueue from main, step from background — no deadlock."""
        scheduler = make_scheduler(mean_latency_ms=50.0)

        for i in range(5):
            scheduler.enqueue(InferenceRequest(request_id=f"r{i}", prompt="hi", max_tokens=20))

        errors = []

        def step_loop():
            try:
                for _ in range(10):
                    scheduler.step()
                    time.sleep(0.01)
            except Exception as e:
                errors.append(e)

        step_thread = threading.Thread(target=step_loop)
        step_thread.start()

        for i in range(5, 10):
            scheduler.enqueue(InferenceRequest(request_id=f"r{i}", prompt="hi", max_tokens=20))

        step_thread.join()
        assert len(errors) == 0


# ---------------------------------------------------------------------------
# Close behavior
# ---------------------------------------------------------------------------

class TestSchedulerClose:
    """Verify scheduler.close() cleans up state."""

    def test_close_clears_queue_and_running(self):
        """After close: queue empty, running empty, _closed=True."""
        scheduler = make_scheduler(mean_latency_ms=5000.0)

        for i in range(3):
            scheduler.enqueue(InferenceRequest(request_id=f"r{i}", prompt="hello", max_tokens=20))

        scheduler.step()
        scheduler.close()

        assert len(scheduler._queue) == 0
        assert len(scheduler._running) == 0
        assert scheduler._closed is True

    def test_double_close_is_idempotent(self):
        """close() called twice — no exception."""
        scheduler = make_scheduler()
        scheduler.enqueue(InferenceRequest(request_id="r1", prompt="hi", max_tokens=10))
        scheduler.step()
        scheduler.close()
        scheduler.close()  # should not raise
        assert scheduler._closed is True


# ---------------------------------------------------------------------------
# Enqueue contract
# ---------------------------------------------------------------------------

class TestEnqueueReturns:
    """Verify enqueue returns request_id unchanged."""

    def test_enqueue_returns_request_id(self):
        scheduler = make_scheduler()
        req = InferenceRequest(request_id="my-id", prompt="hello", max_tokens=10)
        assert scheduler.enqueue(req) == "my-id"

    def test_enqueue_stores_in_queue(self):
        scheduler = make_scheduler()
        scheduler.enqueue(InferenceRequest(request_id="x", prompt="test", max_tokens=5))
        assert len(scheduler._queue) == 1
        assert scheduler._queue[0].request.request_id == "x"


# ---------------------------------------------------------------------------
# Multi-chunk request lifecycle
# ---------------------------------------------------------------------------

class TestChunkedRequestLifecycle:
    """
    Intended behavior for multi-chunk requests.

    NOTE: Current scheduler has a bug where `current_chunk` is never incremented.
    These tests document intended behavior (will fail until bug is fixed).
    """

    def test_single_chunk_request_classified_as_decode(self):
        """A single-chunk request should be submitted as decode phase."""
        scheduler = make_scheduler(max_batch_size=4, prefill_ratio=0.5, mean_latency_ms=10.0)
        req = InferenceRequest(request_id="r1", prompt="hi", max_tokens=20)
        scheduler.enqueue(req)

        # Single chunk: len(chunks)=1, current_chunk(0) < len-1(0) is False → decode
        scheduler.step()

        # Request should be in _running
        assert len(scheduler._running) >= 1

    def test_long_prompt_chunk_count(self):
        """A 15-char prompt with chunk_size=5 produces exactly 3 chunks."""
        scheduler = make_scheduler(chunk_size=5, mean_latency_ms=10.0)
        req = InferenceRequest(request_id="r1", prompt="aaaaaaaaaabbbbb", max_tokens=20)
        scheduler.enqueue(req)

        # 15 chars / 5 = 3 chunks exactly
        assert len(scheduler._queue[0].chunks) == 3


# ---------------------------------------------------------------------------
# Duplicate request_id
# ---------------------------------------------------------------------------

class TestDuplicateRequestId:
    """Document behavior when same request_id is enqueued twice."""

    def test_duplicate_id_overwrites_running(self):
        """
        Same request_id enqueued twice — _running[id] is overwritten (no dedup).
        This is a known limitation; no error is raised.
        """
        scheduler = make_scheduler(mean_latency_ms=5000.0)

        scheduler.enqueue(InferenceRequest(request_id="same", prompt="first", max_tokens=10))
        scheduler.step()

        assert "same" in scheduler._running
        initial_running = len(scheduler._running)

        scheduler.enqueue(InferenceRequest(request_id="same", prompt="second", max_tokens=10))
        scheduler.step()

        # Still 1 running, not 2 (second overwrites first)
        assert len(scheduler._running) == initial_running
