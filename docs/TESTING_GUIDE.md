# TESTING_GUIDE.md — 测试指南

---

## 1. 测试框架

| 工具 | 版本 | 用途 |
|------|------|------|
| pytest | ≥7.4.0 | 测试运行器 |
| pytest-mock | ≥3.12.0 | Mock 桩（替代 unittest.mock） |
| prometheus-client | ≥0.19.0 | Mock metrics 客户端 |

---

## 2. 测试分类与命令

| 分类 | 命令 | 运行环境 |
|------|------|---------|
| Mock 测试（无 GPU） | `pytest tests/ -m mock -v` | 本地（无需 GPU） |
| 单元测试 | `pytest tests/unit/ -v` | 本地（无需 GPU） |
| 集成测试 | `pytest tests/integration/ -v` | **需 GPU** |
| SWE-bench 评测 | `python tests/benchmark_swe.py --output results.json` | **需 GPU** |
| 全部测试 | `pytest tests/ -v` | — |

### pytest 标记（Markers）

| Marker | 用途 |
|--------|------|
| `@pytest.mark.mock` | 无 GPU 的 Mock 测试，使用 `MockInferenceEngine` |
| `@pytest.mark.unit` | 单元测试（不依赖外部服务） |
| `@pytest.mark.integration` | 集成测试（依赖 vLLM 实例） |
| `@pytest.mark.benchmark` | SWE-bench 性能基准测试 |

---

## 3. Mock 测试说明

无 GPU 环境下，所有调用 vLLM 的代码使用 `MockInferenceEngine` 模拟：

```python
# 定义于 docs/brainstorming/04-api-contracts.md
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

Mock 测试覆盖：
- scheduler 的分块逻辑
- kv_cache_manager 的 LRU 淘汰
- metrics_exporter 的指标记录
- 控制层 gRPC Mock 接口

---

## 4. 测试文件命名与位置

```
tests/
├── conftest.py                 # pytest 配置 + fixtures
├── unit/                       # 单元测试
│   ├── test_scheduler.py       # scheduler.py 测试
│   ├── test_kv_cache_manager.py
│   ├── test_inference_engine.py
│   └── test_metrics_exporter.py
├── integration/                # 集成测试
│   ├── test_scheduler_engine.py
│   └── test_batching.py
├── benchmark_swe.py           # SWE-bench 评测脚本
└── mock/                       # Mock 测试（可与 unit 合并）
    └── test_mock_inference.py
```

---

## 5. 覆盖率目标

| 模块 | 覆盖率目标 |
|------|----------|
| `scheduler.py` | ≥ 80% |
| `kv_cache_manager.py` | ≥ 80% |
| `inference_engine.py` | ≥ 70% |
| `metrics_exporter.py` | ≥ 70% |
| `control/tuner_interface.py` | ≥ 60% |
| 整体 | ≥ 75% |

运行覆盖率：`pytest tests/ --cov=src --cov-report=term-missing`

---

## 6. Fixture 规范（conftest.py）

```python
import pytest
from unittest.mock import MagicMock

@pytest.fixture
def mock_inference_engine():
    """提供 MockInferenceEngine 实例。"""
    return MockInferenceEngine()

@pytest.fixture
def scheduler_instance(mock_inference_engine):
    """提供配置好的 Scheduler 实例。"""
    return Scheduler(
        engine=mock_inference_engine,
        chunk_size=512,
        max_batch_size=32,
    )
```

---

## 7. 测试驱动开发（TDD）流程

1. **写测试**：先写 `test_xxx.py`，定义期望行为
2. **运行测试**：确认新测试失败（红色）
3. **写实现**：写最少量代码让测试通过
4. **重构**：清理代码，保持测试绿色
5. **提交**：测试和实现同步提交

---

## 8. CI 测试要求

提交 PR 前，以下测试必须通过：
- `pytest tests/unit/ -v`
- `pytest tests/ -m mock -v`

集成测试和 benchmark 在合并后 CI 执行。

---

## 9. 已知测试缺口（待实现）

- ❌ `tests/unit/test_scheduler.py` — 占位符
- ❌ `tests/unit/test_kv_cache_manager.py` — 占位符
- ❌ `tests/integration/` — 所有文件为占位符
- ❌ `tests/conftest.py` — 占位符

**建议的测试优先顺序**（TDD 顺序）：
1. `kv_cache_manager.py` LRU 逻辑
2. `scheduler.py` Chunked Prefill 分块
3. `scheduler.py` Continuous Batching 调度
4. `metrics_exporter.py` 指标记录
5. `inference_engine.py` vLLM 封装
