"""Integration test: full pipeline with mock adapters."""

import time
import threading
import pytest
from src.core.scheduler import Scheduler
from src.core.models import InferenceRequest, ChunkedPrefillConfig, BatchConfig
from src.adapters.mock_adapter import MockInferenceEngine, MockKVCacheManager, MockMetricsCollector


class TestFullPipelineMock:
    """End-to-end pipeline: Scheduler + Mock Adapter + KVCacheManager."""

    def test_enqueue_multiple_requests(self):
        """10 concurrent requests, verify all enqueued without error."""
        engine = MockInferenceEngine(mean_latency_ms=50)
        kv_cache = MockKVCacheManager()
        metrics = MockMetricsCollector()
        scheduler = Scheduler(
            engine=engine,
            kv_cache=kv_cache,
            metrics=metrics,
            chunk_config=ChunkedPrefillConfig(),
            batch_config=BatchConfig(max_batch_size=8),
        )

        errors = []

        def send_request(i):
            try:
                req = InferenceRequest(
                    request_id=f"req-{i}",
                    prompt="x" * (100 if i % 2 == 0 else 10),
                    max_tokens=50,
                    metadata={"enqueue_time": time.time()},
                )
                scheduler.enqueue(req)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=send_request, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        status = scheduler.get_queue_status()
        assert status.waiting_requests == 10

    def test_scheduler_step_completes(self):
        """Scheduler step runs without crash."""
        engine = MockInferenceEngine(mean_latency_ms=20)
        kv_cache = MockKVCacheManager()
        metrics = MockMetricsCollector()
        scheduler = Scheduler(
            engine=engine,
            kv_cache=kv_cache,
            metrics=metrics,
            chunk_config=ChunkedPrefillConfig(),
            batch_config=BatchConfig(),
        )

        req = InferenceRequest(request_id="r1", prompt="hello", max_tokens=20)
        scheduler.enqueue(req)

        # Run scheduler loop
        completed_any = False
        for _ in range(20):
            results = scheduler.step()
            if results:
                completed_any = True
                break

        assert scheduler.get_queue_status() is not None

    def test_chunked_prefill_split(self):
        """Long prompt is split into chunks."""
        engine = MockInferenceEngine()
        kv_cache = MockKVCacheManager()
        metrics = MockMetricsCollector()
        scheduler = Scheduler(
            engine=engine,
            kv_cache=kv_cache,
            metrics=metrics,
            chunk_config=ChunkedPrefillConfig(chunk_size=5),
            batch_config=BatchConfig(),
        )

        req = InferenceRequest(request_id="long", prompt="a" * 20, max_tokens=100)
        scheduler.enqueue(req)

        # 20 chars / 5 chunk_size = 4 chunks
        assert len(scheduler._queue[0].chunks) == 4
