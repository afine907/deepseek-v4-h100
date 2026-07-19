"""Prometheus metrics collector (aligns with docs/brainstorming/04-api-contracts.md §3)."""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest


class PrometheusMetrics:
    """Prometheus metrics for DeepSeek-V4-Flash inference system."""

    REQUEST_TOTAL = Counter(
        "inference_requests_total",
        "Total number of inference requests",
    )
    REQUEST_FAILED = Counter(
        "inference_requests_failed_total",
        "Total number of failed inference requests",
    )
    KV_CACHE_EVICTED = Counter(
        "kv_cache_blocks_evicted_total",
        "Total number of evicted KV cache blocks",
    )
    QUEUE_LENGTH = Gauge(
        "inference_queue_length",
        "Current number of requests in queue",
    )
    GPU_MEMORY_USED = Gauge(
        "gpu_memory_used_bytes",
        "GPU memory usage in bytes",
    )
    KV_CACHE_HIT_RATE = Gauge(
        "kv_cache_hit_rate",
        "KV cache hit rate (0.0 to 1.0)",
    )
    ACTIVE_REQUESTS = Gauge(
        "active_requests",
        "Number of currently active requests",
    )
    REQUEST_LATENCY_MS = Histogram(
        "inference_latency_ms",
        "Inference latency in milliseconds",
        buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000, 10000],
    )
    PREFILL_LATENCY_MS = Histogram(
        "prefill_latency_ms",
        "Prefill phase latency in milliseconds",
        buckets=[5, 10, 20, 50, 100, 200, 500, 1000],
    )
    DECODE_LATENCY_MS = Histogram(
        "decode_latency_ms",
        "Decode phase latency in milliseconds",
        buckets=[5, 10, 20, 50, 100, 200, 500, 1000],
    )
    TTFT_MS = Histogram(
        "time_to_first_token_ms",
        "Time to first token in milliseconds",
        buckets=[10, 50, 100, 200, 500, 1000, 2000, 5000],
    )
    TOKENS_GENERATED = Counter(
        "tokens_generated_total",
        "Total number of tokens generated",
    )

    @staticmethod
    def get_metrics() -> bytes:
        """Return Prometheus metrics in exposition format."""
        return generate_latest()

    @staticmethod
    def content_type() -> str:
        """Return Prometheus content type."""
        return CONTENT_TYPE_LATEST
