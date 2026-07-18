# scheduler.py — Chunked Prefill + Continuous Batching 调度器

> ⏳ 本模块为占位符，待实现。

---

## 模块职责

`scheduler.py` 是整个推理系统的**调度中枢**，负责：

1. **接收推理请求** — 通过 `SchedulerEngineAPI` 暴露接口
2. **Chunked Prefill** — 将长输入（>512 tokens）切分为 512-token 块
3. **Continuous Batching** — 动态将请求加入批次，最大 32 请求
4. **调度决策** — SJF + aging 反饥饿策略
5. **分发至 vLLM** — 通过 `inference_engine.py` 调用

---

## 公开接口

### SchedulerEngineAPI

```python
class SchedulerEngineAPI:
    def submit(self, request: InferenceRequest) -> str:
        """提交推理请求，返回 request_id。"""

    def get_result(self, request_id: str) -> InferenceResponse | None:
        """非阻塞获取推理结果。"""

    def cancel(self, request_id: str) -> bool:
        """取消请求。"""

    def get_queue_status(self) -> QueueStatus:
        """获取当前排队状态。"""
```

### 数据结构

```python
@dataclass
class InferenceRequest:
    request_id: str
    prompt: str
    max_tokens: int
    temperature: float = 0.7
    metadata: dict  # priority, source, etc.

@dataclass
class InferenceResponse:
    request_id: str
    generated_text: str
    finish_reason: str  # "stop" | "length" | "timeout"
    latency_ms: float
    tokens_generated: int

@dataclass
class QueueStatus:
    waiting_requests: int
    running_requests: int
    avg_wait_time_ms: float
    avg_decode_time_ms: float
```

---

## 核心逻辑

### Chunked Prefill

```
请求输入（假设 2048 tokens）
    │
    ▼
chunk_size = 512 tokens/块
    │
    ├── 块 0：tokens[0:512]   → 送入 vLLM Prefill
    ├── 块 1：tokens[512:1024] → 送入 vLLM Prefill
    ├── 块 2：tokens[1024:1536] → 送入 vLLM Prefill
    └── 块 3：tokens[1536:2048] → 送入 vLLM Prefill
                                        │
                                        ▼
                                    Decode
```

**关键参数**：
- `chunk_size: 512`（tokens/块）
- `max_chunks_per_request: 64`（单请求最大块数）

### Continuous Batching

- `max_batch_size: 32`（单批最大请求数）
- `max_wait_time_ms: 100`（凑批超时）
- `prefill_ratio: 0.3`（Prefill GPU 时间占比上限）

**策略**：当等待中的 prefill 请求 GPU 时间占比超过 0.3 时，强制触发批次调度。

### 反饥饿机制

SJF（Shortest Job First）按 `max_tokens` 排序，aging 每 5 个调度周期将等待时间长的请求优先级 +1。

---

## 依赖关系

```
scheduler.py
├── inference_engine.py (SchedulerEngineAPI)
├── kv_cache_manager.py (allocate/evict blocks)
└── metrics_exporter.py (record scheduling metrics)
```

---

## 配置参数（来源：configs/scheduler.yaml）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `chunk_size` | 512 | Prefill 块大小（tokens） |
| `max_chunks_per_request` | 64 | 单请求最大块数 |
| `max_batch_size` | 32 | 单批最大请求数 |
| `max_wait_time_ms` | 100 | 凑批超时 |
| `prefill_ratio` | 0.3 | Prefill GPU 时间占比上限 |

---

## 测试

```bash
pytest tests/unit/test_scheduler.py -v
pytest tests/ -m mock -v  # 使用 MockInferenceEngine
```

---

## 状态

⏳ **待实现** — 接口定义见 [docs/brainstorming/04-api-contracts.md](../docs/brainstorming/04-api-contracts.md)
