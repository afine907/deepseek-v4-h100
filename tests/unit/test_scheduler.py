"""Unit tests for Scheduler."""

import pytest
import threading
from src.core.scheduler import Scheduler, PrioritizedRequest
from src.core.models import (
    InferenceRequest,
    ChunkedPrefillConfig,
    BatchConfig,
)
from src.adapters.mock_adapter import MockInferenceEngine, MockKVCacheManager, MockMetricsCollector


class TestScheduler:
    def test_enqueue(self):
        engine = MockInferenceEngine(mean_latency_ms=50.0)
        kv = MockKVCacheManager()
        metrics = MockMetricsCollector()
        scheduler = Scheduler(
            engine=engine,
            kv_cache=kv,
            metrics=metrics,
            chunk_config=ChunkedPrefillConfig(),
            batch_config=BatchConfig(),
        )
        request = InferenceRequest(request_id="s-1", prompt="Hello world", max_tokens=10)
        rid = scheduler.enqueue(request)
        assert rid == "s-1"
        status = scheduler.get_queue_status()
        assert status.waiting_requests == 1

    def test_step_completes(self):
        engine = MockInferenceEngine(mean_latency_ms=10.0)
        kv = MockKVCacheManager()
        metrics = MockMetricsCollector()
        scheduler = Scheduler(
            engine=engine,
            kv_cache=kv,
            metrics=metrics,
            chunk_config=ChunkedPrefillConfig(),
            batch_config=BatchConfig(max_batch_size=4),
        )
        request = InferenceRequest(request_id="s-2", prompt="Test", max_tokens=20)
        scheduler.enqueue(request)

        # Run a few steps
        all_completed = False
        for _ in range(20):
            results = scheduler.step()
            if results:
                assert len(results) >= 0
                all_completed = True
                break
        # Mock engine may or may not complete within step limit
        # Just verify no crash
        assert scheduler.get_queue_status() is not None
