"""EvalPipeline — orchestration layer for the benchmarking system."""

import json
import logging
import time
from pathlib import Path

from ..core.models import BatchConfig, ChunkedPrefillConfig
from ..core.ports import InferenceEngine
from ..core.scheduler import Scheduler

logger = logging.getLogger(__name__)


class EvalPipeline:
    """
    Orchestration layer for the evaluation system.

    Usage:
        pipeline = EvalPipeline(
            adapter=MockInferenceEngine(),
            scheduler_config={"chunk_size": 512, "prefill_ratio": 0.3},
            output_dir=Path("output/eval"),
        )
        report_path = pipeline.run(num_runs=3, num_requests=100)
    """

    def __init__(
        self,
        adapter: InferenceEngine,
        scheduler_config: dict | None = None,
        output_dir: str | Path = "output/eval",
    ):
        self._adapter = adapter
        self._scheduler_config = scheduler_config or {}
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

        # Lazy imports to avoid hard dependencies
        self._aggregator = None
        self._charts = None
        self._reporter = None

    def _create_scheduler(self) -> Scheduler:
        """Create scheduler with the configured adapter."""
        from ..adapters.mock_adapter import MockKVCacheManager, MockMetricsCollector

        adapter_name = type(self._adapter).__name__

        if adapter_name == "MockInferenceEngine":
            kv_cache = MockKVCacheManager(
                capacity_blocks=100,
                high_watermark=self._scheduler_config.get("kv_cache_high_watermark", 0.90),
                low_watermark=self._scheduler_config.get("kv_cache_low_watermark", 0.75),
            )
            metrics = MockMetricsCollector()
        else:
            # Real adapter path
            from ..core.kv_cache_manager import KVCacheManager
            from ..core.models import KVCacheConfig

            kv_cache_cfg = KVCacheConfig(
                high_watermark=self._scheduler_config.get("kv_cache_high_watermark", 0.90),
                low_watermark=self._scheduler_config.get("kv_cache_low_watermark", 0.75),
            )
            kv_cache = KVCacheManager(config=kv_cache_cfg)
            metrics = MockMetricsCollector()

        chunk_config = ChunkedPrefillConfig(
            chunk_size=self._scheduler_config.get("chunk_size", 512),
            max_chunks_per_request=self._scheduler_config.get("max_chunks_per_request", 64),
            prefill_ratio=self._scheduler_config.get("prefill_ratio", 0.3),
        )
        batch_config = BatchConfig(
            max_batch_size=self._scheduler_config.get("max_batch_size", 32),
            prefill_ratio=self._scheduler_config.get("prefill_ratio", 0.3),
            max_wait_time_ms=self._scheduler_config.get("max_wait_time_ms", 100),
        )

        return Scheduler(
            engine=self._adapter,
            kv_cache=kv_cache,
            metrics=metrics,
            chunk_config=chunk_config,
            batch_config=batch_config,
        )

    def _run_single_benchmark(
        self, scheduler: Scheduler, num_requests: int, short_ratio: float
    ) -> dict:
        """Run a single benchmark iteration and return a result dict."""
        from ..core.models import InferenceRequest

        latencies = []
        short_tokens = 500
        long_tokens = 8000
        start_time = time.time()

        # Submit requests
        for i in range(num_requests):
            tokens = short_tokens if (i / num_requests) < short_ratio else long_tokens
            req = InferenceRequest(
                request_id=f"bench-{i}",
                prompt="x = 1" * (tokens // 4),
                max_tokens=50,
            )
            scheduler.enqueue(req)

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
        qps = num_requests / duration if duration > 0 else 0

        # Cache hit rate from kv_cache (not from metrics collector)
        cache_hit_rate = scheduler._kv_cache.get_hit_rate()

        return {
            "p50_ms": p50,
            "p90_ms": p90,
            "p99_ms": p99,
            "qps": qps,
            "cache_hit_rate": cache_hit_rate,
            "gpu_util": 0.0,  # populated by real vLLM adapter
            "total_requests": num_requests,
            "completed_requests": completed,
            "duration_sec": round(duration, 2),
        }

    def run(
        self,
        num_runs: int = 3,
        num_requests: int = 100,
        short_ratio: float = 0.6,
    ) -> Path:
        """
        Run the full evaluation pipeline.

        Returns: Path to generated Markdown report.
        """
        from ..eval.aggregator import MetricsAggregator
        from ..eval.charts import ChartGenerator
        from ..eval.reporter import ReportGenerator

        logger.info(f"Starting EvalPipeline: {num_runs} runs × {num_requests} requests")

        # Step 1: Warm-up
        logger.info("Warm-up run...")
        scheduler = self._create_scheduler()
        self._run_single_benchmark(scheduler, num_requests=10, short_ratio=short_ratio)

        # Step 2: Run benchmarks
        logger.info(f"Running {num_runs} benchmark iterations...")
        aggregator = MetricsAggregator()

        all_latencies = []
        convergence_rounds = []
        convergence_p99s = []

        for i in range(num_runs):
            logger.info(f"  Run {i + 1}/{num_runs}...")
            scheduler = self._create_scheduler()
            result = self._run_single_benchmark(scheduler, num_requests, short_ratio)
            aggregator.add_run(result)
            all_latencies.extend([result["p50_ms"]])  # approximate
            convergence_rounds.append(i + 1)
            convergence_p99s.append(result["p99_ms"])
            logger.info(
                f"  Run {i + 1} complete: P99={result['p99_ms']:.1f}ms QPS={result['qps']:.1f}"
            )

        # Step 3: Aggregate
        logger.info("Aggregating results...")
        aggregated = aggregator.aggregate()
        aggregated_dict = aggregated.to_dict()
        logger.info(f"Aggregated: {aggregated_dict}")

        # Save aggregated JSON
        agg_path = self._output_dir / "metrics_aggregated.json"
        agg_path.parent.mkdir(parents=True, exist_ok=True)
        agg_path.write_text(json.dumps(aggregated_dict, indent=2))
        logger.info(f"Aggregated metrics saved: {agg_path}")

        # Step 4: Generate charts
        logger.info("Generating charts...")
        charts = ChartGenerator(output_dir=self._output_dir)

        hit_rate = next((r.mean for r in aggregated.results if r.metric == "cache_hit_rate"), 0)
        qps_mean = next((r.mean for r in aggregated.results if r.metric == "qps"), 0)

        # QPS vs batch size
        qps_by_batch = {str(self._scheduler_config.get("max_batch_size", 32)): qps_mean}

        chart_paths = charts.generate_all(
            latency_data={"latencies": all_latencies},
            qps_data=qps_by_batch,
            hit_rate=hit_rate,
            convergence_data=(convergence_rounds, convergence_p99s),
            sensitivity_data={},  # filled by sensitivity analysis
        )
        logger.info(f"Charts generated: {list(chart_paths.keys())}")

        # Step 5: Generate report
        logger.info("Generating report...")
        reporter = ReportGenerator()
        config = {
            "Adapter": type(self._adapter).__name__,
            "num_requests": num_requests,
            "num_runs": num_runs,
            "short_ratio": short_ratio,
            **self._scheduler_config,
        }
        report_path = self._output_dir / "report.md"
        reporter.generate(
            aggregated=aggregated,
            chart_paths=chart_paths,
            output_path=report_path,
            config=config,
        )
        logger.info(f"Report generated: {report_path}")

        return report_path
