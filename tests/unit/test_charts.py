"""Tests for ChartGenerator."""
from pathlib import Path

import pytest

from src.eval.charts import ChartGenerator, CAT_PALETTE, SEQ_BLUE


class TestChartGenerator:
    def test_init_creates_charts_dir(self, tmp_path):
        cg = ChartGenerator(tmp_path)
        assert cg.charts_dir == tmp_path / "charts"
        assert cg.charts_dir.exists()

    def test_latency_distribution_buckets(self, tmp_path):
        """Empty list produces all-zero buckets."""
        cg = ChartGenerator(tmp_path)
        path = cg.generate_latency_distribution([])
        assert path.suffix == ".png"
        assert path.exists()

    def test_latency_distribution_with_data(self, tmp_path):
        """Known latencies map to correct buckets."""
        cg = ChartGenerator(tmp_path)
        # <100ms: 1, 100-500ms: 2, 500-1000ms: 1, >1000ms: 1
        latencies = [50.0, 150.0, 300.0, 600.0, 1500.0]
        path = cg.generate_latency_distribution(latencies)
        assert path.exists()

    def test_qps_comparison(self, tmp_path):
        cg = ChartGenerator(tmp_path)
        path = cg.generate_qps_comparison({"8": 12.5, "16": 18.3})
        assert path.exists()

    def test_cache_hit_rate(self, tmp_path):
        cg = ChartGenerator(tmp_path)
        path = cg.generate_cache_hit_rate(0.72)
        assert path.exists()

    def test_convergence_curve(self, tmp_path):
        cg = ChartGenerator(tmp_path)
        path = cg.generate_convergence_curve([1, 2, 3], [5000, 4000, 3500])
        assert path.exists()

    def test_sensitivity_heatmap(self, tmp_path):
        cg = ChartGenerator(tmp_path)
        data = {(8, 256): 4200, (16, 256): 3800, (32, 256): 3600}
        path = cg.generate_sensitivity_heatmap(data)
        assert path.exists()

    def test_generate_all(self, tmp_path):
        cg = ChartGenerator(tmp_path)
        paths = cg.generate_all(
            latency_data={"latencies": [100, 200, 300]},
            qps_data={"8": 10.0, "16": 15.0},
            hit_rate=0.68,
            convergence_data=([1, 2], [5000, 4000]),
            sensitivity_data={(8, 256): 4000},
        )
        assert len(paths) == 5
        for p in paths.values():
            assert p.exists()

    def test_generate_all_partial(self, tmp_path):
        """Passing empty data skips that chart."""
        cg = ChartGenerator(tmp_path)
        paths = cg.generate_all(
            latency_data={},
            qps_data={"8": 10.0},
            hit_rate=None,
            convergence_data=(),
            sensitivity_data={},
        )
        assert len(paths) == 1
        assert "qps_comparison" in paths

    def test_palette_values(self):
        """CAT_PALETTE has 4 colors, SEQ_BLUE has 4 steps."""
        assert len(CAT_PALETTE) == 4
        assert len(SEQ_BLUE) == 4
        # All are valid hex colors
        for c in CAT_PALETTE + SEQ_BLUE:
            assert c.startswith("#")
            assert len(c) == 7
