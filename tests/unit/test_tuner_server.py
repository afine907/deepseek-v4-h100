"""Tests for tuner_server REST API."""
import pytest
from fastapi.testclient import TestClient

from src.control.tuner_server import (
    app,
    set_scheduler,
    get_scheduler,
    UpdateConfigRequest,
)
from src.core.models import QueueStatus


class FakeScheduler:
    """Minimal scheduler stub for tests."""

    def __init__(self):
        self._queue_status = QueueStatus(
            waiting_requests=3,
            running_requests=1,
            avg_wait_time_ms=50.0,
            avg_decode_time_ms=120.0,
        )

    def get_queue_status(self) -> QueueStatus:
        return self._queue_status


@pytest.fixture
def client():
    """Test client with a fake scheduler wired in."""
    scheduler = FakeScheduler()
    set_scheduler(scheduler)
    with TestClient(app) as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_status(client):
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["queue"]["waiting"] == 3
    assert data["queue"]["running"] == 1


def test_update_config(client):
    resp = client.post("/config", json={"batch_size": 64, "prefill_ratio": 0.4})
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["applied_config"]["batch_size"] == 64
    assert data["applied_config"]["prefill_ratio"] == 0.4


def test_update_config_partial(client):
    resp = client.post("/config", json={"chunk_size": 256})
    assert resp.status_code == 200
    data = resp.json()
    assert data["applied_config"]["chunk_size"] == 256


def test_metrics(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus format is text/plain
    assert resp.headers["content-type"].startswith("text/plain")
    body = resp.text
    # Should contain at least one metric name
    assert "inference_requests_total" in body or "inference_latency_ms" in body or body == ""


def test_reset(client):
    resp = client.post("/reset")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
