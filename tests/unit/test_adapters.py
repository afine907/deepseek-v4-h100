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


# ---------------------------------------------------------------------------
# Additional MockInferenceEngine concurrency and edge-case tests
# ---------------------------------------------------------------------------

class TestMockInferenceEngineConcurrency:
    """Concurrency tests for MockInferenceEngine."""

    def test_concurrent_submit_same_id(self):
        """Multiple threads submitting same request_id — no crash, result retrievable."""
        import threading
        engine = MockInferenceEngine(mean_latency_ms=20.0)
        request = InferenceRequest(request_id="shared", prompt="hello", max_tokens=10)
        results = []
        errors = []

        def submit_and_get():
            try:
                engine.submit(request)
                r = engine.get_result("shared", timeout=5.0)
                if r is not None:
                    results.append(r.request_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=submit_and_get) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(results) >= 1  # at least one completed

    def test_get_result_timeout_returns_none(self):
        """get_result with very short timeout on a long-latency engine returns None."""
        engine = MockInferenceEngine(mean_latency_ms=5000.0)  # 5 seconds
        request = InferenceRequest(request_id="long-lat", prompt="hello", max_tokens=10)
        engine.submit(request)

        # Immediate timeout — should return None (not done yet)
        result = engine.get_result("long-lat", timeout=0.001)
        assert result is None

    def test_get_result_returns_none_for_unknown_id(self):
        """Unknown request_id returns None without error."""
        engine = MockInferenceEngine(mean_latency_ms=50.0)
        result = engine.get_result("does-not-exist", timeout=0.1)
        assert result is None

    def test_multiple_requests_complete_in_order(self):
        """Submit 3 requests, verify all complete with correct IDs."""
        engine = MockInferenceEngine(mean_latency_ms=20.0)
        request_ids = ["req-a", "req-b", "req-c"]

        for rid in request_ids:
            engine.submit(InferenceRequest(request_id=rid, prompt="hi", max_tokens=10))

        completed = set()
        for _ in range(50):
            for rid in request_ids:
                r = engine.get_result(rid, timeout=0.1)
                if r is not None:
                    completed.add(r.request_id)
            if len(completed) == 3:
                break

        assert completed == {"req-a", "req-b", "req-c"}

    def test_cancel_nonexistent_id_returns_false(self):
        """cancel() for unknown ID returns False, not an exception."""
        engine = MockInferenceEngine(mean_latency_ms=1000.0)
        assert engine.cancel("no-such-id") is False

    def test_submit_with_empty_string_id(self):
        """Empty string request_id falls through to auto-generated ID (falsy check)."""
        engine = MockInferenceEngine(mean_latency_ms=20.0)
        request = InferenceRequest(request_id="", prompt="hello", max_tokens=10)
        rid = engine.submit(request)

        # "" is falsy → or expression returns the auto-generated fallback
        assert rid.startswith("mock-")

        result = engine.get_result(rid, timeout=5.0)
        assert result is not None
        assert result.request_id == rid
