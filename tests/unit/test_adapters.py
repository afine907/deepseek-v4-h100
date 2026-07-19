"""Unit tests for adapters."""

import time
import pytest
from src.adapters.mock_adapter import MockInferenceEngine, MockMetricsCollector
from src.core.models import InferenceRequest, EngineStatus


class TestMockInferenceEngineSubmitGet:
    """Test MockInferenceEngine submit and get_result."""

    def test_submit_returns_id(self):
        engine = MockInferenceEngine(mean_latency_ms=50)
        req = InferenceRequest(request_id="t1", prompt="Hello", max_tokens=10)
        rid = engine.submit(req)
        assert rid == "t1"

    def test_get_result_waits_for_latency(self):
        engine = MockInferenceEngine(mean_latency_ms=100)
        req = InferenceRequest(request_id="t2", prompt="Hi", max_tokens=10)
        engine.submit(req)
        # Immediately should not be done
        result = engine.get_result("t2", timeout=0.001)
        assert result is None
        # After waiting, should complete
        result = engine.get_result("t2", timeout=5.0)
        assert result is not None
        assert result.request_id == "t2"


class TestMockInferenceEngineStatus:
    def test_status_fields(self):
        engine = MockInferenceEngine()
        status = engine.get_status()
        assert isinstance(status, EngineStatus)
        assert status.ready is True
        assert status.model_loaded is True
        assert status.device == "mock"


class TestMockMetricsCollector:
    def test_latency_and_throughput(self):
        mc = MockMetricsCollector()
        mc.record_latency(100.0)
        mc.record_latency(200.0)
        mc.record_throughput(50)
        metrics = mc.get_metrics()
        assert metrics["requests_total"] == 2
        assert metrics["tokens_total"] == 50
        assert "inference_latency_ms_p50" in metrics
        assert "inference_latency_ms_p99" in metrics

    def test_empty_metrics(self):
        mc = MockMetricsCollector()
        metrics = mc.get_metrics()
        assert metrics["requests_total"] == 0
        assert metrics["tokens_total"] == 0
