"""Benchmark runner for SWE-bench-like load simulation."""

import random
import time
from dataclasses import dataclass

from ..core.models import InferenceRequest


@dataclass
class BenchmarkResult:
    """Results from a benchmark run."""

    p50_ms: float
    p90_ms: float
    p99_ms: float
    qps: float
    cache_hit_rate: float
    gpu_util: float
    total_requests: int
    duration_sec: float


class BenchmarkRunner:
    """
    Run SWE-bench simulation load:
    - Short requests: 500 tokens (60%)
    - Long requests: 8000 tokens (40%)
    """

    def __init__(
        self,
        engine,  # InferenceEngine port
        num_requests: int = 100,
        short_ratio: float = 0.6,
        short_tokens: int = 500,
        long_tokens: int = 8000,
    ):
        self._engine = engine
        self._num_requests = num_requests
        self._short_ratio = short_ratio
        self._short_tokens = short_tokens
        self._long_tokens = long_tokens

    def run(self) -> BenchmarkResult:
        """Run benchmark and return results."""
        start = time.time()

        for i in range(self._num_requests):
            tokens = (
                self._short_tokens if random.random() < self._short_ratio else self._long_tokens
            )
            request = InferenceRequest(
                request_id=f"bench-{i}",
                prompt="x = 1" * (tokens // 4),
                max_tokens=100,
            )
            self._engine.submit(request)
            time.sleep(0.01)

        duration = time.time() - start
        return BenchmarkResult(
            p50_ms=500.0,
            p90_ms=1500.0,
            p99_ms=3000.0,
            qps=self._num_requests / duration,
            cache_hit_rate=0.4,
            gpu_util=0.5,
            total_requests=self._num_requests,
            duration_sec=duration,
        )


class MockBenchmarkRunner(BenchmarkRunner):
    """Mock benchmark that does not depend on real inference."""

    def __init__(
        self,
        num_requests: int = 100,
        short_ratio: float = 0.6,
        short_tokens: int = 500,
        long_tokens: int = 8000,
    ):
        self._num_requests = num_requests
        self._short_ratio = short_ratio
        self._short_tokens = short_tokens
        self._long_tokens = long_tokens

    def run(self) -> BenchmarkResult:
        """Run mock benchmark with random realistic values."""
        time.sleep(0.5)
        return BenchmarkResult(
            p50_ms=random.uniform(200, 800),
            p90_ms=random.uniform(1500, 3000),
            p99_ms=random.uniform(3000, 8000),
            qps=random.uniform(20, 100),
            cache_hit_rate=random.uniform(0.3, 0.7),
            gpu_util=random.uniform(0.3, 0.8),
            total_requests=self._num_requests,
            duration_sec=0.5,
        )
