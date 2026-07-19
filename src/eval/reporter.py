"""Markdown report generator for benchmark results."""

import logging
from pathlib import Path

from .aggregator import AggregatedMetrics

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generate structured Markdown benchmark reports.

    Sections:
    1. Executive Summary
    2. Benchmark Configuration
    3. Metrics Table (p50/p90/p99/QPS/cache_hit_rate with delta vs baseline)
    4. Charts (embedded PNG references)
    5. Conclusion & Next Steps
    """

    def __init__(self, template: str | None = None):
        self._template = template or self._DEFAULT_TEMPLATE

    def generate(
        self,
        aggregated: AggregatedMetrics,
        chart_paths: dict[str, Path],
        output_path: Path,
        config: dict | None = None,
        baseline: dict | None = None,
    ) -> None:
        """Generate Markdown report and write to output_path."""
        config = config or {}
        baseline = baseline or {}

        sections = []

        # Section 1: Executive Summary
        sections.append(self._build_executive_summary(aggregated))

        # Section 2: Benchmark Configuration
        sections.append(self._build_config(config))

        # Section 3: Metrics Table
        sections.append(self._build_metrics_table(aggregated, baseline))

        # Section 4: Charts
        sections.append(self._build_charts(chart_paths))

        # Section 5: Conclusion
        sections.append(self._build_conclusion(aggregated))

        report = "\n\n".join(sections)
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        logger.info(f"Report generated: {output_path}")

    def _build_executive_summary(self, aggregated: AggregatedMetrics) -> str:
        p99 = next((r.mean for r in aggregated.results if r.metric == "p99_ms"), 0)
        qps = next((r.mean for r in aggregated.results if r.metric == "qps"), 0)
        hit = next((r.mean for r in aggregated.results if r.metric == "cache_hit_rate"), 0)
        return f"""## Executive Summary

This benchmark evaluated the DeepSeek-V4-Flash inference system on Qwen3.5-0.8B
with {aggregated.runs} run(s). Key findings:

- **P99 latency:** {p99:.1f}ms (target: <5000ms) — {"✅" if p99 < 5000 else "❌"}
- **QPS:** {qps:.1f} req/s
- **KV Cache hit rate:** {hit:.1%}
- **Runs aggregated:** {aggregated.runs}

The evaluation covered latency distribution, throughput, and cache efficiency.
Charts are presented in Section 4.
"""

    def _build_config(self, config: dict) -> str:
        lines = ["## Benchmark Configuration\n", "| Parameter | Value |", "|-----------|-------|"]
        for k, v in config.items():
            lines.append(f"| {k} | {v} |")
        return "\n".join(lines)

    def _build_metrics_table(self, aggregated: AggregatedMetrics, baseline: dict) -> str:
        lines = [
            "## Metrics\n",
            "| Metric | Mean | Std | Min | Max | Delta vs Baseline |",
            "|--------|------|-----|-----|-----|-------------------|",
        ]

        metric_labels = {
            "p50_ms": "P50 Latency (ms)",
            "p90_ms": "P90 Latency (ms)",
            "p99_ms": "P99 Latency (ms)",
            "qps": "QPS",
            "cache_hit_rate": "Cache Hit Rate",
            "gpu_util": "GPU Utilization",
        }

        for r in aggregated.results:
            label = metric_labels.get(r.metric, r.metric)
            base_val = baseline.get(r.metric, None)
            delta_str = ""
            if base_val is not None and base_val != 0:
                delta_pct = ((r.mean - base_val) / base_val) * 100
                delta_str = f"{delta_pct:+.1f}%"
            lines.append(
                f"| {label} | {r.mean:.2f} | {r.std:.2f} | {r.min_val:.2f} | {r.max_val:.2f} | {delta_str} |"
            )

        return "\n".join(lines)

    def _build_charts(self, chart_paths: dict[str, Path]) -> str:
        lines = ["## Charts\n"]
        if not chart_paths:
            lines.append("_No charts generated._")
            return "\n".join(lines)

        chart_titles = {
            "latency_dist": "Latency Distribution",
            "qps_comparison": "QPS vs Batch Size",
            "cache_hit_rate": "KV Cache Hit Rate",
            "convergence": "P99 Convergence Curve",
            "sensitivity": "Parameter Sensitivity Heatmap",
        }

        for key, path in chart_paths.items():
            title = chart_titles.get(key, key)
            rel_path = path.name
            lines.append(f"### {title}\n")
            lines.append(f"![{title}](./charts/{rel_path})\n")

        return "\n".join(lines)

    def _build_conclusion(self, aggregated: AggregatedMetrics) -> str:
        p99 = next((r.mean for r in aggregated.results if r.metric == "p99_ms"), 0)
        qps = next((r.mean for r in aggregated.results if r.metric == "qps"), 0)
        hit = next((r.mean for r in aggregated.results if r.metric == "cache_hit_rate"), 0)

        p99_ok = "✅ P99 is within target (<5000ms)" if p99 < 5000 else "❌ P99 exceeds target"
        qps_ok = "✅ QPS meets target (>100)" if qps > 100 else "⚠️ QPS below target"
        hit_ok = (
            "✅ Cache hit rate meets target (>70%)"
            if hit > 0.7
            else "⚠️ Cache hit rate below target"
        )
        status_items = "\n".join([f"- {ok}" for ok in [p99_ok, qps_ok, hit_ok]])

        return f"""## Conclusion & Next Steps

### Status
{status_items}

### Observations
- Latency: P99 at {p99:.1f}ms shows {"acceptable" if p99 < 5000 else "room for improvement"}
- Throughput: {qps:.1f} QPS
- Cache efficiency: {hit:.1%} hit rate

### Next Steps
1. Analyze P99 outliers for root cause
2. Tune `chunk_size` and `prefill_ratio` if latency is high
3. Increase `max_batch_size` if GPU utilization is low
4. Validate on DeepSeek-V4-Flash (8×H100) once Qwen3.5-0.8B results are satisfactory
"""

    _DEFAULT_TEMPLATE = """
# Benchmark Report

Generated by EvalPipeline
"""
