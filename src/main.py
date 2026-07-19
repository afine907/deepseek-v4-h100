"""DeepSeek-V4-Flash inference system — main entry point."""

import argparse
import logging
import time

from src.config.settings import get_settings
from src.core.models import BatchConfig, ChunkedPrefillConfig, KVCacheConfig
from src.core.scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_mock_mode() -> Scheduler:
    """Create a scheduler in mock mode (no vLLM dependency)."""
    from src.adapters.mock_adapter import (
        MockInferenceEngine,
        MockKVCacheManager,
        MockMetricsCollector,
    )

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
    logger.info(
        f"Queue status: waiting={status.waiting_requests}, running={status.running_requests}"
    )


def run_server(scheduler: Scheduler, host: str = "0.0.0.0", port: int = 8000) -> None:
    """Run the FastAPI control server."""
    import uvicorn

    from src.control.tuner_server import app, set_scheduler

    set_scheduler(scheduler)
    logger.info(f"Starting control server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


def main_tune_mode(args) -> None:
    """Run the tuning agent in mock or real mode."""
    from src.agent.benchmark_runner import BenchmarkRunner, MockBenchmarkRunner
    from src.agent.tuner_agent import TunerAgent
    from src.config.settings import get_settings
    from src.control.tuner_interface import RESTTuner

    settings = get_settings()

    # Choose benchmark runner
    if args.backend == "mock":
        runner = MockBenchmarkRunner(num_requests=args.num_requests)
    else:
        # Real benchmark runner needs an engine
        scheduler = create_vllm_mode()
        runner = BenchmarkRunner(engine=scheduler, num_requests=args.num_requests)

    # Choose LLM provider
    llm_provider = args.agent_provider or settings.agent.llm_provider
    llm_model = settings.agent.model_name

    tuner = RESTTuner(base_url=args.tuner_url)
    initial_config = {
        "batch_size": settings.batching.max_batch_size,
        "chunk_size": 512,
        "kv_cache_high_watermark": settings.kv_cache.high_watermark,
        "prefill_ratio": settings.batching.prefill_ratio,
    }

    agent = TunerAgent(
        tuner_interface=tuner,
        benchmark_runner=runner,
        config=initial_config,
        max_iterations=args.max_iterations,
        llm_provider=llm_provider,
        llm_model=llm_model,
    )

    result = agent.tune()
    logger.info(f"Tuning complete: converged={result.converged}, rounds={result.total_rounds}")
    logger.info(f"Final config: {result.final_config}")


def main() -> None:
    parser = argparse.ArgumentParser(description="DeepSeek-V4-Flash inference system")
    parser.add_argument(
        "--mode",
        choices=["mock", "server", "tune"],
        default="mock",
        help="mock: demo with MockInferenceEngine; server: vLLM adapter; tune: LLM Agent tuning",
    )
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument(
        "--backend",
        default="mock",
        help="mock: MockBenchmarkRunner; real: BenchmarkRunner with engine",
    )
    parser.add_argument("--tuner-url", default="http://localhost:8000", help="Tuner server URL")
    parser.add_argument(
        "--agent-provider",
        choices=["claude", "openai", "mock"],
        help="LLM provider for tuning decisions",
    )
    parser.add_argument("--max-iterations", type=int, default=10, help="Max tuning iterations")
    parser.add_argument("--num-requests", type=int, default=100, help="Requests per benchmark run")
    args = parser.parse_args()

    settings = get_settings()
    logger.info(f"Config loaded — backend={settings.model.backend}, model={settings.model.name}")

    if args.mode == "mock":
        scheduler = create_mock_mode()
        run_mock_demo(scheduler)
    elif args.mode == "server":
        scheduler = create_vllm_mode()
        run_server(scheduler, host=args.host, port=args.port)
    else:  # tune
        main_tune_mode(args)


if __name__ == "__main__":
    main()
