"""Chart generation using dataviz skill principles."""

import logging
from pathlib import Path

# dataviz skill validated palette
CAT_PALETTE = ["#2a78d6", "#008300", "#e87ba4", "#eda100"]
SEQ_BLUE = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab"]
STATUS_GOOD = "#0ca30c"
STATUS_WARNING = "#fab219"

logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generate PNG charts following dataviz skill specifications:
    - Thin marks (≤24px bars, 2px lines, ≥8px markers)
    - 2px surface gap between bars
    - Validated categorical palette
    - Sequential = single hue light→dark
    """

    def __init__(self, output_dir: Path):
        self._output_dir = Path(output_dir)
        self._charts_dir = self._output_dir / "charts"
        self._charts_dir.mkdir(parents=True, exist_ok=True)

    @property
    def charts_dir(self) -> Path:
        return self._charts_dir

    def generate_latency_distribution(
        self, latencies: list[float], output_name: str = "latency_dist.png"
    ) -> Path:
        """Bar chart: latency bucket distribution (<100 / 100-500 / 500-1000 / >1000ms)."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        buckets = {"<100ms": 0, "100-500ms": 0, "500-1000ms": 0, ">1000ms": 0}
        for lat in latencies:
            if lat < 100:
                buckets["<100ms"] += 1
            elif lat < 500:
                buckets["100-500ms"] += 1
            elif lat < 1000:
                buckets["500-1000ms"] += 1
            else:
                buckets[">1000ms"] += 1

        labels = list(buckets.keys())
        values = list(buckets.values())

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.set_facecolor("#fcfcfb")
        fig.patch.set_facecolor("#fcfcfb")

        bars = ax.bar(labels, values, color=CAT_PALETTE[0], width=0.6, edgecolor="none")
        # Thin bars: cap at ~20px
        max_val = max(values) if values else 1
        for bar in bars:
            if max_val > 20:
                bar.set_height(20.0 * bar.get_height() / max_val)

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#e1e0d9")
        ax.spines["bottom"].set_color("#e1e0d9")
        ax.tick_params(colors="#52514e")
        ax.yaxis.grid(True, color="#e1e0d9", linewidth=1)
        ax.set_axisbelow(True)

        ax.set_ylabel("Request count", color="#52514e")
        ax.set_xlabel("Latency bucket", color="#52514e")
        ax.set_title("Latency Distribution", color="#0b0b0b", fontsize=14, fontweight="bold")

        plt.tight_layout()
        path = self._charts_dir / output_name
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        logger.info(f"Latency distribution chart saved: {path}")
        return path

    def generate_qps_comparison(
        self, qps_by_batch: dict[str, float], output_name: str = "qps_comparison.png"
    ) -> Path:
        """Grouped bar chart: QPS by batch size (baseline vs optimized)."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        batch_sizes = sorted(qps_by_batch.keys())
        values = [qps_by_batch[k] for k in batch_sizes]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.set_facecolor("#fcfcfb")
        fig.patch.set_facecolor("#fcfcfb")

        ax.bar(range(len(batch_sizes)), values, color=CAT_PALETTE[0], width=0.5, edgecolor="none")
        ax.set_xticks(range(len(batch_sizes)))
        ax.set_xticklabels(batch_sizes)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#e1e0d9")
        ax.spines["bottom"].set_color("#e1e0d9")
        ax.tick_params(colors="#52514e")
        ax.yaxis.grid(True, color="#e1e0d9", linewidth=1)
        ax.set_axisbelow(True)

        ax.set_ylabel("QPS", color="#52514e")
        ax.set_xlabel("Batch size", color="#52514e")
        ax.set_title("QPS vs Batch Size", color="#0b0b0b", fontsize=14, fontweight="bold")

        # Selective direct labels
        max_idx = values.index(max(values))
        ax.annotate(
            f"{values[max_idx]:.1f}",
            xy=(max_idx, values[max_idx]),
            xytext=(0, 5),
            textcoords="offset points",
            ha="center",
            color="#52514e",
            fontsize=9,
        )

        plt.tight_layout()
        path = self._charts_dir / output_name
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        logger.info(f"QPS comparison chart saved: {path}")
        return path

    def generate_cache_hit_rate(
        self, hit_rate: float, output_name: str = "cache_hit_rate.png"
    ) -> Path:
        """Stat tile: cache hit rate with target line at 0.70."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(6, 4))
        ax.set_facecolor("#fcfcfb")
        fig.patch.set_facecolor("#fcfcfb")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        # Background track (light sequential)
        ax.barh(0.5, 1.0, height=0.3, color=SEQ_BLUE[0], edgecolor="none")

        # Fill to hit_rate
        ax.barh(0.5, hit_rate, height=0.3, color=CAT_PALETTE[0], edgecolor="none")

        # Target line at 0.70
        ax.axvline(x=0.70, color=STATUS_GOOD, linewidth=2, linestyle="--", label="Target 70%")

        # Value text
        ax.text(
            hit_rate - 0.05,
            0.5,
            f"{hit_rate:.1%}",
            va="center",
            ha="right",
            color="white",
            fontsize=18,
            fontweight="bold",
        )

        ax.set_title("KV Cache Hit Rate", color="#0b0b0b", fontsize=14, fontweight="bold")
        ax.axis("off")
        ax.legend(loc="lower right")

        plt.tight_layout()
        path = self._charts_dir / output_name
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        logger.info(f"Cache hit rate chart saved: {path}")
        return path

    def generate_convergence_curve(
        self, rounds: list[int], p99_latencies: list[float], output_name: str = "convergence.png"
    ) -> Path:
        """Line chart: P99 latency convergence over tuning rounds."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.set_facecolor("#fcfcfb")
        fig.patch.set_facecolor("#fcfcfb")

        ax.plot(rounds, p99_latencies, color=CAT_PALETTE[0], linewidth=2, marker="o", markersize=8)
        ax.fill_between(rounds, p99_latencies, alpha=0.1, color=CAT_PALETTE[0])

        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#e1e0d9")
        ax.spines["bottom"].set_color("#e1e0d9")
        ax.tick_params(colors="#52514e")
        ax.yaxis.grid(True, color="#e1e0d9", linewidth=1)
        ax.set_axisbelow(True)

        ax.set_ylabel("P99 latency (ms)", color="#52514e")
        ax.set_xlabel("Tuning round", color="#52514e")
        ax.set_title("P99 Latency Convergence", color="#0b0b0b", fontsize=14, fontweight="bold")

        # Target line at 5000ms
        ax.axhline(
            y=5000,
            color="#e34948",
            linewidth=1.5,
            linestyle="--",
            alpha=0.7,
            label="Target <5000ms",
        )
        ax.legend()

        plt.tight_layout()
        path = self._charts_dir / output_name
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        logger.info(f"Convergence curve saved: {path}")
        return path

    def generate_sensitivity_heatmap(
        self, data: dict[tuple[int, int], float], output_name: str = "sensitivity_heatmap.png"
    ) -> Path:
        """Heatmap: batch_size × chunk_size → P99 latency."""
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

        batch_sizes = sorted(set(k[0] for k in data.keys()))
        chunk_sizes = sorted(set(k[1] for k in data.keys()))

        z = np.zeros((len(chunk_sizes), len(batch_sizes)))
        for (bs, cs), val in data.items():
            bi = batch_sizes.index(bs)
            ci = chunk_sizes.index(cs)
            z[ci, bi] = val

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_facecolor("#fcfcfb")
        fig.patch.set_facecolor("#fcfcfb")

        im = ax.imshow(z, cmap="Blues", aspect="auto", interpolation="nearest")
        ax.set_xticks(range(len(batch_sizes)))
        ax.set_xticklabels(batch_sizes)
        ax.set_yticks(range(len(chunk_sizes)))
        ax.set_yticklabels(chunk_sizes)
        ax.set_xlabel("Batch size", color="#52514e")
        ax.set_ylabel("Chunk size", color="#52514e")
        ax.set_title(
            "Parameter Sensitivity: P99 Latency (ms)",
            color="#0b0b0b",
            fontsize=14,
            fontweight="bold",
        )

        # Colorbar
        cbar = fig.colorbar(im, ax=ax, shrink=0.8)
        cbar.set_label("P99 latency (ms)", color="#52514e")
        cbar.ax.tick_params(colors="#52514e")

        # Selective direct labels
        for i in range(len(chunk_sizes)):
            for j in range(len(batch_sizes)):
                val = z[i, j]
                if val > 0:
                    ax.text(
                        j,
                        i,
                        f"{val:.0f}",
                        ha="center",
                        va="center",
                        color="white" if val > z.mean() else "#0b0b0b",
                        fontsize=8,
                    )

        plt.tight_layout()
        path = self._charts_dir / output_name
        plt.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close()
        logger.info(f"Sensitivity heatmap saved: {path}")
        return path

    def generate_all(
        self,
        latency_data: dict,
        qps_data: dict,
        hit_rate: float,
        convergence_data: tuple,
        sensitivity_data: dict,
    ) -> dict[str, Path]:
        """Generate all charts. Returns dict of chart_name -> file_path."""
        paths = {}
        if latency_data:
            paths["latency_dist"] = self.generate_latency_distribution(
                latency_data.get("latencies", [])
            )
        if qps_data:
            paths["qps_comparison"] = self.generate_qps_comparison(qps_data)
        if hit_rate is not None:
            paths["cache_hit_rate"] = self.generate_cache_hit_rate(hit_rate)
        if convergence_data:
            rounds, p99s = convergence_data
            paths["convergence"] = self.generate_convergence_curve(rounds, p99s)
        if sensitivity_data:
            paths["sensitivity"] = self.generate_sensitivity_heatmap(sensitivity_data)
        return paths
