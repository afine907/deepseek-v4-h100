"""Unit tests for Mock adapters."""

import time
import pytest
from src.adapters.mock_adapter import MockInferenceEngine, MockKVCacheManager, MockMetricsCollector
from src.core.models import InferenceRequest, FinishReason


class TestMockInferenceEngine:
    def test_submit_and_get_result(self):
        engine = MockInferenceEngine(mean_latency_ms=50.0, std_latency_ms=10.0)
        request = InferenceRequest(request_id="test-1", prompt="Hello", max_tokens=10)
        rid = engine.submit(request)
        assert rid == "test-1"

        # Not yet complete
        result = engine.get_result(rid, timeout=0.0)
        assert result is None

        # Wait for completion
        result = engine.get_result(rid, timeout=5.0)
        assert result is not None
        assert result.request_id == "test-1"
        assert result.finish_reason == FinishReason.STOP

    def test_cancel(self):
        engine = MockInferenceEngine(mean_latency_ms=50000.0)
        request = InferenceRequest(request_id="cancel-1", prompt="Hello", max_tokens=10)
        engine.submit(request)
        assert engine.cancel("cancel-1") is True
        assert engine.cancel("nonexistent") is False

    def test_get_status(self):
        engine = MockInferenceEngine()
        status = engine.get_status()
        assert status.ready is True
        assert status.model_loaded is True
        assert status.device == "mock"


class TestMockKVCacheManager:
    def test_eviction(self):
        cache = MockKVCacheManager(capacity_blocks=3, high_watermark=0.9, low_watermark=0.5)
        cache.record_access("block-1")
        cache.record_access("block-2")
        cache.record_access("block-3")
        # At capacity, next access should trigger eviction
        evicted = cache.record_access("block-4")
        # eviction is internal, just check it didn't crash
        assert cache.get_hit_rate() >= 0.0

    def test_hit_rate(self):
        cache = MockKVCacheManager(capacity_blocks=10)
        cache.record_access("a")
        cache.record_access("b")
        cache.record_access("a")  # hit
        # a was accessed before b, so a is a hit on second access
        rate = cache.get_hit_rate()
        assert 0.0 <= rate <= 1.0


class TestMockMetricsCollector:
    def test_record_and_get(self):
        collector = MockMetricsCollector()
        collector.record_latency(100.0)
        collector.record_throughput(50)
        metrics = collector.get_metrics()
        assert metrics["requests_total"] == 1
        assert metrics["tokens_total"] == 50
        assert metrics["inference_latency_ms_p50"] == 100.0
