"""FastAPI control server for DeepSeek Tuner (REST API)."""

import threading
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="DeepSeek Tuner Control API")

_config: dict = {}
_config_lock = threading.Lock()


class UpdateConfigRequest(BaseModel):
    """Request to update scheduler / engine configuration."""
    batch_size: Optional[int] = None
    chunk_size: Optional[int] = None
    kv_cache_high_watermark: Optional[float] = None
    kv_cache_low_watermark: Optional[float] = None
    prefill_ratio: Optional[float] = None


@app.get("/status")
def get_status() -> dict:
    """Return current system status."""
    return {
        "ready": True,
        "queue_length": 0,
        "active_requests": 0,
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


@app.get("/metrics")
def get_metrics() -> bytes:
    """Return Prometheus metrics."""
    from ..adapters.metrics import PrometheusMetrics
    return PrometheusMetrics.get_metrics()


@app.post("/reset")
def reset_stats() -> dict:
    """Reset statistics (placeholder)."""
    return {"success": True}
