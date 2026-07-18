# 头脑风暴记录 #04：接口契约定义

> 日期：2026-07-18
> 状态：✅ 初稿，待确认

---

## 四层调用关系总览

```
控制层 (Agent)
    │
    │ 调参指令（batch_size, chunk_size, kv_cache_watermark）
    ▼
┌───────────────────────────────────────────────┐
│               路由与调度层                      │
│   (Scheduler / Chunked Prefill / Batching)    │
│                                                │
│    │ 输入：原始请求 + 调度策略                  │
│    ▼                                          │
│   ┌────────────────────────────────────────┐  │
│   │           推理引擎层                    │  │
│   │      (vLLM / FP8 / TP=8)              │  │
│   └────────────────────────────────────────┘  │
│                                                │
│    │ 输出：推理结果 + 执行指标                 │
│    ▼                                          │
└───────────────────────────────────────────────┘
    │
    │ metrics（prometheus 格式）
    ▼
可观测层 (Prometheus)
```

---

## 接口定义

### 接口 1：控制层 → 调度层

**调用方式：** HTTP REST 或 gRPC（推荐 gRPC，性能更高）

```protobuf
// scheduler_control.proto
service SchedulerControl {
  // 更新调度参数
  rpc UpdateConfig(UpdateConfigRequest) returns (UpdateConfigResponse);
  // 查询当前状态
  rpc GetStatus(GetStatusRequest) returns (GetStatusResponse);
}

message UpdateConfigRequest {
  int32 batch_size = 1;           // 批处理大小
  int32 chunk_size = 2;            // Prefill chunk 大小（tokens）
  float kv_cache_high_watermark = 3; // KV Cache 高水位（0.0~1.0）
  float kv_cache_low_watermark = 4;  // KV Cache 低水位
  int32 max_concurrent_requests = 5; // 最大并发请求数
}

message UpdateConfigResponse {
  bool success = 1;
  string message = 2;
  Config applied_config = 3;  // 实际生效的配置
}
```

### 接口 2：调度层 ↔ 推理引擎层（内部）

**调用方式：** Python 函数调用（同一进程内，或 IPC）

```python
# scheduler_engine_api.py

class InferenceRequest:
    """推理请求"""
    request_id: str
    prompt: str
    max_tokens: int
    temperature: float = 0.7
    metadata: dict  # 可传递优先级、来源等信息


class InferenceResponse:
    """推理响应"""
    request_id: str
    generated_text: str
    finish_reason: str  # "stop" | "length" | "timeout"
    latency_ms: float
    tokens_generated: int


class SchedulerEngineAPI:
    """调度层 → 推理引擎的接口"""

    def submit(self, request: InferenceRequest) -> str:
        """
        提交推理请求
        Returns: request_id（用于后续查询）
        """
        ...

    def get_result(self, request_id: str) -> InferenceResponse:
        """
        获取推理结果（非阻塞）
        Returns: 结果或 None（仍在执行中）
        """
        ...

    def cancel(self, request_id: str) -> bool:
        """取消请求"""
        ...

    def get_queue_status(self) -> QueueStatus:
        """获取排队状态"""
        ...


class QueueStatus:
    waiting_requests: int     # 等待中的请求数
    running_requests: int      # 正在执行的请求数
    avg_wait_time_ms: float   # 平均等待时间
    avg_decode_time_ms: float # 平均解码时间
```

### 接口 3：推理引擎 → 可观测层（Metrics）

**调用方式：** Prometheus Pushgateway 或 OpenTelemetry

```python
# metrics定义

# 计数器（Counter）
REQUEST_TOTAL = "inference_requests_total"          # 总请求数
REQUEST_FAILED = "inference_requests_failed_total"   # 失败请求数
KV_CACHE_EVICTED = "kv_cache_blocks_evicted_total" # 淘汰的 KV Cache block 数

# 仪表盘（Gauge）
QUEUE_LENGTH = "inference_queue_length"             # 当前排队长度
GPU_MEMORY_USED_GB = "gpu_memory_used_bytes"       # GPU 显存占用（bytes，换算 GB）
KV_CACHE_HIT_RATE = "kv_cache_hit_rate"            # KV Cache 命中率（0.0~1.0）
ACTIVE_REQUESTS = "active_requests"                 # 当前活跃请求数

# 直方图（Histogram）
REQUEST_LATENCY_MS = "inference_latency_ms"         # 推理延迟分布
PREFILL_LATENCY_MS = "prefill_latency_ms"          # Prefill 阶段延迟
DECODE_LATENCY_MS = "decode_latency_ms"            # Decode 阶段延迟
TTFT_MS = "time_to_first_token_ms"                 # 首个 token 产生时间

# 标签（Labels）
REQUEST_LATENCY_MS.labels(stage="prefill" | "decode", chunk_index="0" | "1" | ...)
GPU_MEMORY_USED_GB.labels(gpu_id="0" | "1" | ... | "7")
```

### 接口 4：推理引擎内部指标（Prometheus 格式暴露）

```python
# vLLM 已集成的 metrics 标签对齐
# 额外新增的自定义指标

CUSTOM_CHUNKED_PREFILL_CHUNKS = "chunked_prefill_chunks_total"  # 分块次数
CUSTOM_LONG_REQUEST_BLOCKED = "long_request_blocked_count"      # 长请求阻塞计数
CUSTOM_OOM_EVENTS = "oom_events_total"                         # OOM 事件次数
```

---

## 各层职责边界

| 层 | 职责 | 不管什么 |
|----|------|---------|
| **控制层** | 收集 metrics → 分析 → 调参 | 不直接发请求 |
| **调度层** | 接收请求 → 排队 → 分块 → 调度 | 不做推理 |
| **推理引擎层** | 执行推理 → 返回结果 → 暴露 metrics | 不做调度决策 |
| **可观测层** | 采集 → 存储 → 可视化 | 不改配置 |

---

## 简化版（参赛初期 Mock）

```python
# 如果推理引擎还没接好，用这个 Mock 替代
class MockInferenceEngine:
    def submit(self, request: InferenceRequest) -> str:
        time.sleep(random.uniform(0.1, 2.0))  # 模拟推理延迟
        return request.request_id

    def get_result(self, request_id: str) -> InferenceResponse:
        return InferenceResponse(
            request_id=request_id,
            generated_text="Mock response",
            finish_reason="stop",
            latency_ms=random.uniform(100, 2000),
            tokens_generated=random.randint(50, 500),
        )
```

---

## 决策确认

| # | 问题 | 决策 |
|---|------|------|
| 1 | 控制层通信协议 | **gRPC** ✅ |
| 2 | Streaming 输出 | **不做**（参赛重点在吞吐和延迟） |
| 3 | KV Cache 淘汰回调 | **不做**（控制层靠 Prometheus 轮询） |
| 4 | 调度↔引擎跨进程 | **进程内**（初期快速联调） |
