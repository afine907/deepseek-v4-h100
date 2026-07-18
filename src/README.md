# 源代码目录

> ⏳ 本目录所有文件为占位符，将在开发阶段逐步实现。

## 模块列表

| 文件 | 职责 | 状态 |
|------|------|------|
| `scheduler.py` | 调度层：Chunked Prefill + Continuous Batching | ⏳ 待实现 |
| `kv_cache_manager.py` | KV Cache LRU 淘汰管理 | ⏳ 待实现 |
| `inference_engine.py` | vLLM 引擎封装 | ⏳ 待实现 |
| `metrics_exporter.py` | Prometheus 指标暴露 | ⏳ 待实现 |
| `control/tuner_interface.py` | 调参接口（Mock/预留） | ⏳ 待实现 |

## 架构层次

```
控制层（tuner_interface.py - Mock）
    ↓
路由与调度层（scheduler.py）
    ├── Chunked Prefill（分块预填充）
    └── Continuous Batching（连续批处理）
    ↓
推理引擎层（inference_engine.py → vLLM）
    ↓
可观测层（metrics_exporter.py → Prometheus）
```

## 接口定义

详细接口见 `docs/brainstorming/04-api-contracts.md`

## 开发测试

```bash
# Mock 测试（无 GPU）
pytest tests/ -m mock

# 单元测试
pytest tests/unit/
```
