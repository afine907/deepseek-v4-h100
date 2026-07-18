# metrics_exporter.py — Prometheus 指标导出器

> ⏳ 本模块为占位符，待实现。

---

## 模块职责

`metrics_exporter.py` 负责将推理系统的可观测指标暴露给 Prometheus：

1. **指标定义** — 使用 `prometheus_client` 定义所有指标
2. **HTTP Server** — 在 `/metrics` endpoint 暴露指标
3. **指标记录** — 在推理请求的各个阶段记录指标
4. **自定义指标** — Chunked Prefill、KV Cache 淘汰等系统特有指标

---

## Prometheus 指标定义

### 计数器（Counter）

```python
from prometheus_client import Counter

inference_requests_total = Counter(
    "inference_requests_total",
    "Total number of inference requests",
    ["status"]  # "success" | "failed"
)

kv_cache_blocks_evicted_total = Counter(
    "kv_cache_blocks_evicted_total",
    "Total number of KV cache blocks evicted"
)

chunked_prefill_chunks_total = Counter(
    "chunked_prefill_chunks_total",
    "Total number of prefill chunks processed"
)
```

### 仪表盘（Gauge）

```python
from prometheus_client import Gauge

inference_queue_length = Gauge(
    "inference_queue_length",
    "Current number of requests waiting in queue"
)

gpu_memory_used_bytes = Gauge(
    "gpu_memory_used_bytes",
    "GPU memory usage in bytes",
    ["gpu_id"]  # "0" ~ "7"
)

kv_cache_hit_rate = Gauge(
    "kv_cache_hit_rate",
    "KV cache hit rate (0.0~1.0)"
)

active_requests = Gauge(
    "active_requests",
    "Current number of active inference requests"
)
```

### 直方图（Histogram）

```python
from prometheus_client import Histogram

inference_latency_ms = Histogram(
    "inference_latency_ms",
    "Inference request latency in milliseconds",
    ["stage"]  # "prefill" | "decode" | "total"
)

ttft_ms = Histogram(
    "time_to_first_token_ms",
    "Time to first token in milliseconds"
)
```

---

## 公开接口

```python
class MetricsExporter:
    def __init__(self, port: int = 8000):
        """初始化，启动 /metrics HTTP server。"""

    def record_request_start(self, request_id: str) -> None:
        """记录请求开始。"""

    def record_request_end(
        self,
        request_id: str,
        latency_ms: float,
        tokens_generated: int,
        status: str,
    ) -> None:
        """记录请求结束。"""

    def record_queue_length(self, length: int) -> None:
        """记录当前排队长度。"""

    def record_gpu_memory(self, gpu_id: int, bytes_used: int) -> None:
        """记录 GPU 显存使用。"""

    def record_kv_cache_evict(self, num_blocks: int) -> None:
        """记录 KV Cache 淘汰。"""
```

---

## 部署

`metrics_exporter.py` 启动时在独立线程中运行 HTTP server：

```python
from prometheus_client import start_http_server

start_http_server(port=8001)  # 与 vLLM 端口分开
```

指标 endpoint：`http://localhost:8001/metrics`

---

## 与 vLLM 集成

vLLM 本身已暴露部分 metrics（通过 `--metrics-addr`）。
本模块在 vLLM 基础上**新增**系统特有指标（Chunked Prefill、KV Cache）。

---

## 依赖关系

```
metrics_exporter.py
└── prometheus_client（第三方库）
```

无内部模块依赖（metrics_exporter 被其他模块调用，不反向依赖）。

---

## 测试

```bash
pytest tests/unit/test_metrics_exporter.py -v

# 手动验证
curl http://localhost:8001/metrics | grep inference_
```

---

## 状态

⏳ **待实现**
