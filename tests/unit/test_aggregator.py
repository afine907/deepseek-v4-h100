"""Tests for MetricsAggregator."""
import csv
from pathlib import Path

import pytest

from src.eval.aggregator import (
    MetricsAggregator,
    AggregatedResult,
    AggregatedMetrics,
)


class TestAggregatedResult:
    def test_to_dict_single(self):
        r = AggregatedResult(metric="p50_ms", mean=100.0, std=0.0, min_val=100.0, max_val=100.0, count=1)
        d = r.to_dict()
        assert d["metric"] == "p50_ms"
        assert d["mean"] == 100.0
        assert d["std"] == 0.0
        assert d["min"] == 100.0
        assert d["max"] == 100.0
        assert d["count"] == 1

    def test_to_dict_multiple(self):
        r = AggregatedResult(metric="p50_ms", mean=110.0, std=10.0, min_val=100.0, max_val=120.0, count=5)
        d = r.to_dict()
        assert d["std"] == 10.0


class TestAggregatedMetrics:
    def test_to_dict_empty(self):
        m = AggregatedMetrics()
        d = m.to_dict()
        assert d["runs"] == 0
        assert d["metrics"] == []

    def test_to_dict_with_results(self):
        r = AggregatedResult(metric="p50_ms", mean=100.0, std=5.0, min_val=95.0, max_val=105.0, count=3)
        m = AggregatedMetrics(results=[r], runs=3)
        d = m.to_dict()
        assert d["runs"] == 3
        assert len(d["metrics"]) == 1
        assert d["metrics"][0]["metric"] == "p50_ms"


class TestMetricsAggregator:
    def test_add_run_dict(self):
        agg = MetricsAggregator()
        agg.add_run({"p50_ms": 100.0, "p90_ms": 200.0, "p99_ms": 300.0,
                     "qps": 10.0, "cache_hit_rate": 0.5, "gpu_util": 0.8,
                     "total_requests": 50, "duration_sec": 5.0})
        agg.add_run({"p50_ms": 110.0, "p90_ms": 210.0, "p99_ms": 310.0,
                     "qps": 11.0, "cache_hit_rate": 0.6, "gpu_util": 0.9,
                     "total_requests": 50, "duration_sec": 4.5})
        result = agg.aggregate()
        assert result.runs == 2
        p50 = next(r for r in result.results if r.metric == "p50_ms")
        assert p50.mean == 105.0
        assert p50.min_val == 100.0
        assert p50.max_val == 110.0

    def test_add_run_object_with_attributes(self):
        """BenchmarkResult-like object with attribute access."""
        class FakeResult:
            def __init__(self):
                self.p50_ms = 100.0
                self.p90_ms = 200.0
                self.p99_ms = 300.0
                self.qps = 10.0
                self.cache_hit_rate = 0.5
                self.gpu_util = 0.8
                self.total_requests = 50
                self.duration_sec = 5.0

        agg = MetricsAggregator()
        agg.add_run(FakeResult())
        result = agg.aggregate()
        assert result.runs == 1
        p50 = next(r for r in result.results if r.metric == "p50_ms")
        assert p50.mean == 100.0

    def test_identical_runs_std_is_zero(self):
        """3 identical runs should produce std=0.0 on all metrics."""
        agg = MetricsAggregator()
        identical_run = {"p50_ms": 100.0, "p90_ms": 200.0, "p99_ms": 300.0,
                         "qps": 10.0, "cache_hit_rate": 0.5, "gpu_util": 0.8,
                         "total_requests": 50, "duration_sec": 5.0}
        for _ in range(3):
            agg.add_run(identical_run)
        result = agg.aggregate()
        for r in result.results:
            assert r.std == 0.0, f"{r.metric} expected std=0.0 but got {r.std}"

    def test_to_csv(self, tmp_path):
        agg = MetricsAggregator()
        agg.add_run({"p50_ms": 100.0, "p90_ms": 200.0, "p99_ms": 300.0,
                     "qps": 10.0, "cache_hit_rate": 0.5, "gpu_util": 0.8,
                     "total_requests": 50, "duration_sec": 5.0})
        agg.add_run({"p50_ms": 110.0, "p90_ms": 210.0, "p99_ms": 310.0,
                     "qps": 11.0, "cache_hit_rate": 0.6, "gpu_util": 0.9,
                     "total_requests": 50, "duration_sec": 4.5})
        path = tmp_path / "metrics.csv"
        agg.to_csv(path)
        assert path.exists()
        with open(path) as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 6  # 6 metrics
        p50_row = next(r for r in rows if r["metric"] == "p50_ms")
        assert float(p50_row["mean"]) == 105.0

    def test_empty_aggregate(self):
        agg = MetricsAggregator()
        result = agg.aggregate()
        assert result.runs == 0
        assert result.results == []

    def test_to_dict(self):
        agg = MetricsAggregator()
        agg.add_run({"p50_ms": 100.0, "p90_ms": 200.0, "p99_ms": 300.0,
                     "qps": 10.0, "cache_hit_rate": 0.5, "gpu_util": 0.8,
                     "total_requests": 50, "duration_sec": 5.0})
        d = agg.to_dict()
        assert d["runs"] == 1
        assert len(d["metrics"]) == 6
