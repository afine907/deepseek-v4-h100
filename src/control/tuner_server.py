"""FastAPI control server for DeepSeek Tuner (REST API)."""

import logging
import threading
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from ..adapters.metrics import PrometheusMetrics

logger = logging.getLogger(__name__)

app = FastAPI(title="DeepSeek Tuner Control API")

# Global scheduler reference (set via dependency injection)
_scheduler: Optional["Scheduler"] = None
_scheduler_lock = threading.Lock()

_config: dict = {}
_config_lock = threading.Lock()


def set_scheduler(scheduler: "Scheduler") -> None:
    """Dependency injection for the scheduler — call once at startup."""
    global _scheduler
    with _scheduler_lock:
        _scheduler = scheduler
    logger.info("Scheduler wired to tuner server")


def get_scheduler() -> "Scheduler":
    """Get the current scheduler instance."""
    if _scheduler is None:
        raise HTTPException(status_code=503, detail="Scheduler not initialized")
    return _scheduler


class UpdateConfigRequest(BaseModel):
    """Request to update scheduler / engine configuration."""
    batch_size: Optional[int] = None
    chunk_size: Optional[int] = None
    kv_cache_high_watermark: Optional[float] = None
    kv_cache_low_watermark: Optional[float] = None
    prefill_ratio: Optional[float] = None


@app.get("/health")
def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok"}


@app.get("/status")
def get_status() -> dict:
    """Return current system status."""
    scheduler = get_scheduler()
    qs = scheduler.get_queue_status()
    return {
        "ready": True,
        "queue": {
            "waiting": qs.waiting_requests,
            "running": qs.running_requests,
        },
    }


@app.post("/config")
def update_config(req: UpdateConfigRequest) -> dict:
    """Update scheduling / cache parameters."""
    with _config_lock:
        if req.batch_size is not None:
            _config["batch_size"] = req.batch_size
        if req.chunk_size is not None:
            _config["chunk_size"] = req.chunk_size
        if req.kv_cache_high_watermark is not None:
            _config["kv_cache_high_watermark"] = req.kv_cache_high_watermark
        if req.kv_cache_low_watermark is not None:
            _config["kv_cache_low_watermark"] = req.kv_cache_low_watermark
        if req.prefill_ratio is not None:
            _config["prefill_ratio"] = req.prefill_ratio
    return {"success": True, "applied_config": dict(_config)}


@app.get("/metrics", response_class=PlainTextResponse)
def get_metrics() -> PlainTextResponse:
    """Return Prometheus metrics in exposition format."""
    return PlainTextResponse(
        content=PrometheusMetrics.get_metrics().decode(),
        media_type=PrometheusMetrics.content_type(),
    )


@app.post("/reset")
def reset_stats() -> dict:
    """Reset statistics (placeholder)."""
    return {"success": True}
