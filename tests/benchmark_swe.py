#!/usr/bin/env python3
"""SWE-bench benchmark script — standalone executable.

Usage:
    python tests/benchmark_swe.py --adapter mock --output results.json --num-requests 100
    python tests/benchmark_swe.py --adapter vllm --model Qwen/Qwen3.5-0.8B --output results.json
"""
import argparse
import json
import logging
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.models import InferenceRequest, ChunkedPrefillConfig, BatchConfig, KVCacheConfig
from src.core.scheduler import Scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def create_scheduler(adapter_type: str, model: str):
    """Create scheduler with specified adapter."""
    if adapter_type == "mock":
        from src.adapters.mock_adapter import MockInferenceEngine, MockKVCacheManager, MockMetricsCollector

        engine = MockInferenceEngine(mean_latency_ms=200.0, std_latency_ms=50.0)
        kv_cache = MockKVCacheManager(capacity_blocks=100, high_watermark=0.90, low_watermark=0.75)
        metrics = MockMetricsCollector()
    elif adapter_type == "vllm":
        from src.adapters.vllm_adapter import VLLMAdapter
        from src.core.kv_cache_manager import KVCacheManager

        engine = VLLMAdapter(
            model_name=model,
            dtype="bfloat16",
            tensor_parallel_size=1,  # CPU mode
            max_model_len=512,
            gpu_memory_utilization=0.5,
            max_batch_size=4,
        )
        kv_cache_cfg = KVCacheConfig(high_watermark=0.90, low_watermark=0.75)
        kv_cache = KVCacheManager(config=kv_cache_cfg)
        from src.adapters.mock_adapter import MockMetricsCollector
        metrics = MockMetricsCollector()
    else:
        raise ValueError(f"Unknown adapter: {adapter_type}")

    chunk_config = ChunkedPrefillConfig(chunk_size=512, max_chunks_per_request=64, prefill_ratio=0.3)
    batch_config = BatchConfig(max_batch_size=32, prefill_ratio=0.3, max_wait_time_ms=100)

    return Scheduler(
        engine=engine,
        kv_cache=kv_cache,
        metrics=metrics,
        chunk_config=chunk_config,
        batch_config=batch_config,
    )


def run_benchmark(scheduler: Scheduler, num_requests: int, short_ratio: float) -> dict:
    """Run benchmark and return metrics dict."""
    latencies = []
    short_tokens = 500
    long_tokens = 8000

    # Warm-up
    warmup_count = max(1, num_requests // 10)
    for i in range(min(5, warmup_count)):
        req = InferenceRequest(
            request_id=f"warmup-{i}",
            prompt="x = 1",
            max_tokens=20,
        )
        scheduler.enqueue(req)
        for _ in range(20):
            results = scheduler.step()
            for r in results:
                pass  # discard warmup results

    # Timed run
    start_time = time.time()
    request_ids = []

    for i in range(num_requests):
        tokens = short_tokens if (i / num_requests) < short_ratio else long_tokens
        req = InferenceRequest(
            request_id=f"bench-{i}",
            prompt="x = 1" * (tokens // 4),
            max_tokens=50,
            metadata={"enqueue_time": time.time()},
        )
        scheduler.enqueue(req)
        request_ids.append(req.request_id)

    # Collect results
    completed = 0
    max_steps = 200
    step_count = 0
    while completed < num_requests and step_count < max_steps:
        results = scheduler.step()
        for r in results:
            latencies.append(r.latency_ms)
            completed += 1
        step_count += 1
        if not results:
            time.sleep(0.01)

    duration = time.time() - start_time
    latencies.sort()

    n = len(latencies)
    p50 = latencies[n // 2] if n > 0 else 0
    p90 = latencies[int(n * 0.90)] if n > 0 else 0
    p99 = latencies[int(n * 0.99)] if n > 0 else 0

    # Cache hit rate from kv_cache
    cache_hit_rate = scheduler._kv_cache.get_hit_rate()

    qps = num_requests / duration if duration > 0 else 0

    return {
        "p50_ms": p50,
        "p90_ms": p90,
        "p99_ms": p99,
        "qps": qps,
        "cache_hit_rate": cache_hit_rate,
        "gpu_util": 0.0,  # not available in mock mode; populated by real vLLM adapter
        "total_requests": num_requests,
        "completed_requests": completed,
        "duration_sec": round(duration, 2),
    }


def main():
    parser = argparse.ArgumentParser(description="SWE-bench benchmark script")
    parser.add_argument("--output", type=str, required=True, help="Output JSON file path")
    parser.add_argument("--adapter", type=str, default="mock", choices=["mock", "vllm"])
    parser.add_argument("--model", type=str, default="Qwen/Qwen3.5-0.8B")
    parser.add_argument("--num-requests", type=int, default=100)
    parser.add_argument("--short-ratio", type=float, default=0.6)
    args = parser.parse_args()

    logger.info(
        f"Starting benchmark: adapter={args.adapter}, model={args.model}, "
        f"requests={args.num_requests}, short_ratio={args.short_ratio}"
    )
    scheduler = create_scheduler(args.adapter, args.model)
    results = run_benchmark(scheduler, args.num_requests, args.short_ratio)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Results written to {args.output}")
    logger.info(
        f"P50: {results['p50_ms']:.1f}ms | P90: {results['p90_ms']:.1f}ms | "
        f"P99: {results['p99_ms']:.1f}ms | QPS: {results['qps']:.1f}"
    )


if __name__ == "__main__":
    main()
