# ARCHITECTURE.md — 系统架构

---

## 四层架构总览

```
┌──────────────────────────────────────────────┐
│               控制层（Control）               │
│         tuner_interface.py (Mock/预留)         │
│         接收调参指令，暴露配置接口               │
└──────────────────────┬───────────────────────┘
                       │ gRPC（预留/Mock）
                       ▼
┌──────────────────────────────────────────────┐
│           路由与调度层（Routing & Scheduling）   │
│                  scheduler.py                 │
│  ┌─────────────────────────────────────────┐ │
│  │  Chunked Prefill（分块预填充）            │ │
│  │  Continuous Batching（连续批处理）        │ │
│  └─────────────────────────────────────────┘ │
└──────────────────────┬───────────────────────┘
                       │ Python 函数调用
                       ▼
┌──────────────────────────────────────────────┐
│             推理引擎层（Inference Engine）     │
│               inference_engine.py             │
│         vLLM / FP8 / TP=8 / NCCL             │
└──────────────────────┬───────────────────────┘
                       │ Prometheus metrics
                       ▼
┌──────────────────────────────────────────────┐
│              可观测层（Observability）          │
│               metrics_exporter.py             │
│              Prometheus Pushgateway            │
└──────────────────────────────────────────────┘
```

---

## 模块职责

### scheduler.py — 调度层核心

**职责**：接收推理请求 → 分块（Chunked Prefill）→ 加入批次（Continuous Batching）→ 分发至 vLLM

**关键逻辑**：
- 输入切分：按 512 tokens/块拆分长 prefill 请求
- 批次管理：等待 max_batch_size=32 或 max_wait_time=100ms 后触发调度
- 反饥饿：SJF（Shortest Job First）+ aging 机制
- prefill_ratio 上限：0.3（保证 Decode 有足够 GPU 时间）

**接口**：
- `SchedulerEngineAPI.submit(request: InferenceRequest) -> request_id`
- `SchedulerEngineAPI.get_result(request_id) -> InferenceResponse | None`
- `SchedulerEngineAPI.cancel(request_id) -> bool`
- `SchedulerEngineAPI.get_queue_status() -> QueueStatus`

**依赖**：`inference_engine.py`、`kv_cache_manager.py`

---

### kv_cache_manager.py — KV Cache 管理

**职责**：管理 vLLM 的 KV Cache 块生命周期，LRU 淘汰策略

**关键逻辑**：
- 显存水位监控（high_watermark=0.90, low_watermark=0.75）
- Block-level 淘汰粒度
- 与 vLLM 交互，管理 block 分配/释放

**接口**：
- `KVCacheManager.allocate(request_id, num_blocks)`
- `KVCacheManager.evict()` — LRU 淘汰
- `KVCacheManager.get_status() -> {used_blocks, available_blocks, hit_rate}`

**依赖**：调用 vLLM 内部 API（通过 `inference_engine.py` 暴露）

---

### inference_engine.py — vLLM 封装

**职责**：封装 vLLM 的 Python API，提供同步/异步推理接口

**关键逻辑**：
- vLLM `LLM` 类初始化（TP=8, FP8, gpu_memory_utilization=0.90）
- `chat()` / `generate()` 调用
- 错误处理（OOM、超时）
- metrics 回调注册

**接口**：
- `InferenceEngine.submit(request: InferenceRequest) -> request_id`
- `InferenceEngine.get_result(request_id) -> InferenceResponse`
- `InferenceEngine.get_stats() -> EngineStats`

**依赖**：vLLM 库（`pip install vllm>=0.6.0`）

---

### metrics_exporter.py — Prometheus 指标

**职责**：暴露推理系统的可观测指标

**关键指标**：

| 类型 | 指标名 | 说明 |
|------|--------|------|
| Counter | `inference_requests_total` | 总请求数 |
| Counter | `inference_requests_failed_total` | 失败请求数 |
| Counter | `kv_cache_blocks_evicted_total` | 淘汰的 KV Cache block 数 |
| Gauge | `inference_queue_length` | 当前排队长度 |
| Gauge | `gpu_memory_used_bytes` | GPU 显存占用 |
| Gauge | `kv_cache_hit_rate` | KV Cache 命中率 |
| Gauge | `active_requests` | 活跃请求数 |
| Histogram | `inference_latency_ms` | 推理延迟分布 |
| Histogram | `prefill_latency_ms` | Prefill 延迟 |
| Histogram | `decode_latency_ms` | Decode 延迟 |
| Histogram | `time_to_first_token_ms` | TTFT |

**接口**：
- `MetricsExporter.start()` — 启动 HTTP server（`/metrics` endpoint）
- `MetricsExporter.record_request(...)` — 记录请求指标
- `MetricsExporter.record_chunked_prefill(...)` — 记录分块指标

---

### control/tuner_interface.py — 调参接口（Mock）

**职责**：预留的控制层调参接口（gRPC），参赛版仅 Mock 实现

**接口**：
- `UpdateConfig(batch_size, chunk_size, kv_cache_watermark)` — 更新调度参数
- `GetStatus()` — 查询当前状态

---

## 数据流

```
HTTP/gRPC 请求
    │
    ▼
scheduler.py: 接收请求，分配 request_id
    │
    ▼
scheduler.py: Chunked Prefill（切分为 512-token 块）
    │
    ▼
scheduler.py: Continuous Batching（加入等待批次）
    │
    ├─→ kv_cache_manager.py: 检查/分配 KV Cache 块
    │
    ▼
inference_engine.py: 调用 vLLM 执行推理
    │
    ├─→ metrics_exporter.py: 记录延迟、GPU 显存等指标
    │
    ▼
返回 InferenceResponse（generated_text, latency_ms, tokens_generated）
```

---

## 配置参数（源码默认值）

见 `configs/` 目录 YAML 文件：

| 文件 | 核心参数 |
|------|---------|
| `model.yaml` | `tensor_parallel_size: 8`, `quantization: FP8`, `gpu_memory_utilization: 0.90` |
| `batching.yaml` | `max_batch_size: 32`, `max_wait_time_ms: 100`, `prefill_ratio: 0.3` |
| `scheduler.yaml` | `chunk_size: 512`, `max_chunks_per_request: 64` |
| `kv_cache.yaml` | `淘汰策略: LRU`, `high_watermark: 0.90`, `low_watermark: 0.75` |

---

## 部署形态

- **Docker 容器**：`nvidia/cuda:12.4.1-runtime-ubuntu22.04`
- **运行时**：在 8×H100 物理机上直接运行容器（不使用 K8s）
- **入口**：`launch_h100.sh` 启动 vLLM + 本系统各模块
- **端口**：8000（vLLM API），metrics 在 `/metrics`
