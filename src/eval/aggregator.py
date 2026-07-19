"""Metrics aggregation across multiple benchmark runs."""
import csv
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


METRIC_NAMES = [
    "p50_ms",
    "p90_ms",
    "p99_ms",
    "qps",
    "cache_hit_rate",
    "gpu_util",
]


@dataclass
class AggregatedResult:
    """Aggregated metrics across multiple runs."""
    metric: str
    mean: float
    std: float
    min_val: float
    max_val: float
    count: int

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "mean": round(self.mean, 4),
            "std": round(self.std, 4) if self.count > 1 else 0.0,
            "min": round(self.min_val, 4),
            "max": round(self.max_val, 4),
            "count": self.count,
        }


@dataclass
class AggregatedMetrics:
    """Full aggregation result."""
    results: list[AggregatedResult] = field(default_factory=list)
    runs: int = 0

    def to_dict(self) -> dict:
        return {
            "runs": self.runs,
            "metrics": [r.to_dict() for r in self.results],
        }

    def to_csv(self, path: Path) -> None:
        if not self.results:
            return
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["metric", "mean", "std", "min", "max", "count"])
            writer.writeheader()
            for r in self.results:
                writer.writerow(r.to_dict())


class MetricsAggregator:
    """
    Aggregate multiple benchmark runs.

    Accepts runs as dicts (from benchmark_swe.py JSON output) or objects
    with attribute access (e.g. BenchmarkResult dataclass).

    Usage:
        agg = MetricsAggregator()
        for _ in range(3):
            result = run_benchmark()  # dict or BenchmarkResult
            agg.add_run(result)
        aggregated = agg.aggregate()
        aggregated.to_csv(Path("metrics.csv"))
    """

    def __init__(self):
        self._runs: list[dict[str, Any]] = []

    def add_run(self, result: dict[str, Any] | Any) -> None:
        """Add a single run result (dict or BenchmarkResult-like object)."""
        run_dict = {}
        for name in METRIC_NAMES:
            val = getattr(result, name, None) if hasattr(result, name) else result.get(name)
            run_dict[name] = val if val is not None else 0.0
        self._runs.append(run_dict)

    def aggregate(self) -> AggregatedMetrics:
        if not self._runs:
            return AggregatedMetrics()

        aggregated = []
        for name in METRIC_NAMES:
            values = [r[name] for r in self._runs if name in r]
            if not values:
                continue
            mean_val = statistics.mean(values)
            std_val = statistics.stdev(values) if len(values) > 1 else 0.0
            aggregated.append(AggregatedResult(
                metric=name,
                mean=mean_val,
                std=std_val,
                min_val=min(values),
                max_val=max(values),
                count=len(values),
            ))

        return AggregatedMetrics(results=aggregated, runs=len(self._runs))

    def to_dict(self) -> dict:
        return self.aggregate().to_dict()

    def to_csv(self, path: Path) -> None:
        self.aggregate().to_csv(path)
