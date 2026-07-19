"""Tests for ReportGenerator."""
from pathlib import Path
import re

import pytest

from src.eval.reporter import ReportGenerator
from src.eval.aggregator import AggregatedMetrics, AggregatedResult


class TestReportGenerator:
    @pytest.fixture
    def sample_aggregated(self):
        return AggregatedMetrics(
            results=[
                AggregatedResult(metric="p50_ms", mean=200.0, std=10.0, min_val=190.0, max_val=210.0, count=3),
                AggregatedResult(metric="p90_ms", mean=250.0, std=5.0, min_val=245.0, max_val=255.0, count=3),
                AggregatedResult(metric="p99_ms", mean=280.0, std=8.0, min_val=272.0, max_val=288.0, count=3),
                AggregatedResult(metric="qps", mean=46.0, std=1.5, min_val=44.5, max_val=47.5, count=3),
                AggregatedResult(metric="cache_hit_rate", mean=0.72, std=0.02, min_val=0.70, max_val=0.74, count=3),
                AggregatedResult(metric="gpu_util", mean=0.0, std=0.0, min_val=0.0, max_val=0.0, count=3),
            ],
            runs=3,
        )

    def test_import(self):
        from src.eval.reporter import ReportGenerator
        assert ReportGenerator is not None

    def test_generate_writes_file(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_report_contains_sections(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        content = out.read_text()
        assert "## Executive Summary" in content
        assert "## Benchmark Configuration" in content
        assert "## Metrics" in content
        assert "## Charts" in content
        assert "## Conclusion & Next Steps" in content

    def test_executive_summary_p99(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        content = out.read_text()
        assert "P99 latency" in content
        assert "✅" in content  # sample P99=280 < 5000

    def test_metrics_table_headers(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        content = out.read_text()
        assert "P50 Latency (ms)" in content
        assert "P99 Latency (ms)" in content
        assert "QPS" in content
        assert "Cache Hit Rate" in content

    def test_config_section(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        config = {"adapter": "mock", "num_requests": 50, "short_ratio": 0.6}
        rg.generate(sample_aggregated, {}, out, config=config)
        content = out.read_text()
        assert "| adapter | mock |" in content
        assert "| num_requests | 50 |" in content

    def test_baseline_delta(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        baseline = {"p99_ms": 300.0}
        rg.generate(sample_aggregated, {}, out, baseline=baseline)
        content = out.read_text()
        # 280 vs 300 baseline = -6.7% improvement
        assert any("%" in line for line in content.split("\n") if "P99" in line)

    def test_charts_section_with_paths(self, tmp_path, sample_aggregated):
        charts = {
            "latency_dist": Path("charts/latency_dist.png"),
            "qps_comparison": Path("charts/qps_comparison.png"),
        }
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, charts, out)
        content = out.read_text()
        assert "Latency Distribution" in content
        assert "./charts/latency_dist.png" in content

    def test_charts_section_empty(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        content = out.read_text()
        assert "_No charts generated._" in content

    def test_conclusion_status(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        content = out.read_text()
        # sample_aggregated: p99=280 (<5000), qps=46 (<100), hit=72% (>70%)
        assert "P99" in content
        assert "QPS" in content
        assert "Cache efficiency" in content

    def test_all_five_sections_present(self, tmp_path, sample_aggregated):
        rg = ReportGenerator()
        out = tmp_path / "report.md"
        rg.generate(sample_aggregated, {}, out)
        content = out.read_text()
        section_count = sum(1 for line in content.split("\n") if re.match(r"^## ", line.strip()))
        assert section_count == 5, f"Expected 5 sections, got {section_count}"
