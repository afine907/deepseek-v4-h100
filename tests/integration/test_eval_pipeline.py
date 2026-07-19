"""Integration test: full EvalPipeline with mock adapter."""
import json
from pathlib import Path

import pytest

from src.adapters.mock_adapter import MockInferenceEngine
from src.eval.pipeline import EvalPipeline


class TestEvalPipeline:
    """End-to-end EvalPipeline integration tests."""

    def test_pipeline_runs_without_error(self, tmp_path):
        """Full pipeline (1 run × 10 requests) completes without exception."""
        adapter = MockInferenceEngine(mean_latency_ms=50.0)
        pipeline = EvalPipeline(
            adapter,
            scheduler_config={"max_batch_size": 16, "chunk_size": 256},
            output_dir=tmp_path,
        )
        report_path = pipeline.run(num_runs=1, num_requests=10)
        assert report_path.exists()

    def test_output_contains_metrics_json(self, tmp_path):
        adapter = MockInferenceEngine(mean_latency_ms=50.0)
        pipeline = EvalPipeline(adapter, output_dir=tmp_path)
        pipeline.run(num_runs=1, num_requests=10)

        metrics_file = tmp_path / "metrics_aggregated.json"
        assert metrics_file.exists()
        data = json.loads(metrics_file.read_text())
        assert data["runs"] == 1
        assert len(data["metrics"]) >= 1

    def test_output_contains_report_md(self, tmp_path):
        adapter = MockInferenceEngine(mean_latency_ms=50.0)
        pipeline = EvalPipeline(adapter, output_dir=tmp_path)
        pipeline.run(num_runs=1, num_requests=10)

        report = tmp_path / "report.md"
        assert report.exists()
        content = report.read_text()
        assert "## Executive Summary" in content
        assert "## Metrics" in content
        assert "## Charts" in content

    def test_output_contains_charts(self, tmp_path):
        adapter = MockInferenceEngine(mean_latency_ms=50.0)
        pipeline = EvalPipeline(adapter, output_dir=tmp_path)
        pipeline.run(num_runs=1, num_requests=10)

        charts_dir = tmp_path / "charts"
        assert charts_dir.exists()
        png_files = list(charts_dir.glob("*.png"))
        assert len(png_files) >= 1

    def test_multiple_runs_aggregated(self, tmp_path):
        adapter = MockInferenceEngine(mean_latency_ms=50.0)
        pipeline = EvalPipeline(adapter, output_dir=tmp_path)
        pipeline.run(num_runs=3, num_requests=10)

        metrics_file = tmp_path / "metrics_aggregated.json"
        data = json.loads(metrics_file.read_text())
        assert data["runs"] == 3

    def test_pipeline_config_passed_to_report(self, tmp_path):
        adapter = MockInferenceEngine(mean_latency_ms=50.0)
        pipeline = EvalPipeline(
            adapter,
            scheduler_config={"chunk_size": 512, "prefill_ratio": 0.3},
            output_dir=tmp_path,
        )
        pipeline.run(num_runs=1, num_requests=10)

        report = tmp_path / "report.md"
        content = report.read_text()
        assert "chunk_size" in content
        assert "prefill_ratio" in content
