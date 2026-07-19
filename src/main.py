"""DeepSeek-V4-Flash inference system — main entry point."""

import argparse
import logging
import sys
import threading
import time

from src.core.models import ChunkedPrefillConfig, BatchConfig, KVCacheConfig
from src.core.scheduler import Scheduler
from src.config.settings import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_mock_mode() -> Scheduler:
    """Create a scheduler in mock mode (no vLLM dependency)."""
    from src.adapters.mock_adapter import MockInferenceEngine, MockKVCacheManager, MockMetricsCollector

    settings = get_settings()

    engine = MockInferenceEngine(mean_latency_ms=200.0, std_latency_ms=50.0)
    kv_cache = MockKVCacheManager(
        capacity_blocks=100,
        high_watermark=settings.kv_cache.high_watermark,
        low_watermark=settings.kv_cache.low_watermark,
    )
    metrics = MockMetricsCollector()

    chunk_config = ChunkedPrefillConfig(
        chunk_size=512,
        max_chunks_per_request=64,
        prefill_ratio=settings.batching.prefill_ratio,
    )
    batch_config = BatchConfig(
        max_batch_size=settings.batching.max_batch_size,
        prefill_ratio=settings.batching.prefill_ratio,
        max_wait_time_ms=settings.batching.max_wait_time_ms,
    )

    scheduler = Scheduler(
        engine=engine,
        kv_cache=kv_cache,
        metrics=metrics,
        chunk_config=chunk_config,
        batch_config=batch_config,
    )
    return scheduler


def create_vllm_mode() -> Scheduler:
    """Create a scheduler with vLLM adapter (CPU or GPU)."""
    from src.adapters.vllm_adapter import VLLMAdapter
    from src.core.kv_cache_manager import KVCacheManager

    settings = get_settings()

    engine = VLLMAdapter(
        model_name=settings.model.name,
        dtype=settings.model.dtype,
        tensor_parallel_size=settings.model.tensor_parallel_size,
        quantization=settings.model.quantization,
        max_model_len=settings.model.max_model_len,
        gpu_memory_utilization=settings.model.gpu_memory_utilization,
        max_batch_size=settings.model.max_num_seqs,
        kv_cache_memory_bytes=settings.model.kv_cache_memory_bytes,
    )

    kv_cache_cfg = KVCacheConfig(
        strategy=settings.kv_cache.strategy,
        high_watermark=settings.kv_cache.high_watermark,
        low_watermark=settings.kv_cache.low_watermark,
        max_evict_per_round=settings.kv_cache.max_evict_per_round,
    )
    kv_cache = KVCacheManager(config=kv_cache_cfg)

    from src.adapters.mock_adapter import MockMetricsCollector
    metrics = MockMetricsCollector()

    chunk_config = ChunkedPrefillConfig(
        chunk_size=512,
        max_chunks_per_request=64,
        prefill_ratio=settings.batching.prefill_ratio,
    )
    batch_config = BatchConfig(
        max_batch_size=settings.batching.max_batch_size,
        prefill_ratio=settings.batching.prefill_ratio,
        max_wait_time_ms=settings.batching.max_wait_time_ms,
    )

    scheduler = Scheduler(
        engine=engine,
        kv_cache=kv_cache,
        metrics=metrics,
        chunk_config=chunk_config,
        batch_config=batch_config,
    )
    return scheduler


def run_mock_demo(scheduler: Scheduler) -> None:
    """Run a simple demo with mock engine."""
    from src.core.models import InferenceRequest

    logger.info("Running mock demo...")

    # Submit a few requests
    request = InferenceRequest(
        request_id="req-1",
        prompt="Hello, world!",
        max_tokens=50,
        temperature=0.7,
    )
    scheduler.enqueue(request)

    # Run scheduler loop
    for _ in range(10):
        results = scheduler.step()
        for r in results:
            logger.info(f"Completed: {r.request_id} -> {r.generated_text[:50]}")
        time.sleep(0.2)

    status = scheduler.get_queue_status()
    logger.info(f"Queue status: waiting={status.waiting_requests}, running={status.running_requests}")


def run_server(scheduler: Scheduler, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI control server."""
    import uvicorn
    from src.control.tuner_server import app

    logger.info(f"Starting control server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek-V4-Flash inference system")
    parser.add_argument(
        "--mode",
        choices=["mock", "server"],
        default="mock",
        help="mock: use MockInferenceEngine (no vLLM); server: use vLLM adapter",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()

    settings = get_settings()
    logger.info(f"Config loaded — backend={settings.model.backend}, model={settings.model.name}")

    if args.mode == "mock":
        scheduler = create_mock_mode()
        run_mock_demo(scheduler)
    else:
        scheduler = create_vllm_mode()
        run_server(scheduler, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
