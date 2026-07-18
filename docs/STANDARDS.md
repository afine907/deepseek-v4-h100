# STANDARDS.md — 编码规范

---

## 1. Python 版本与风格

- **版本**：Python 3.10+
- **风格**：Google Python Style Guide（[中文版](https://google.github.io/styleguide/pyguide.html)）
- **格式化**：Black（line-length=100）
- **导入排序**：isort（标准库 → 第三方 → 本地）

---

## 2. 文件结构

每个 `.py` 文件应包含（按顺序）：

1. 模块 docstring（单行或 Google style 多行）
2. 导入（`logging`, `typing`, 第三方, 本地）
3. 常量（`MAX_CHUNK_SIZE = 512`）
4. 类定义
5. 函数定义
6. `if __name__ == "__main__":`（仅在可执行模块中）

---

## 3. 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块 | `snake_case` | `kv_cache_manager.py` |
| 类 | `CapWords` | `InferenceEngine`, `KVCacheManager` |
| 函数/方法 | `snake_case` | `submit_request()`, `evict_blocks()` |
| 常量 | `UPPER_SNAKE_CASE` | `MAX_BATCH_SIZE`, `DEFAULT_CHUNK_SIZE` |
| 变量 | `snake_case` | `request_id`, `gpu_memory_used` |
| 私有成员 | `_leading_underscore` | `_evict_lru_block()` |
| 类型别名 | `CapWords` | `QueueStatus`, `InferenceRequest` |

---

## 4. 类型注解

- 所有公开函数和方法的参数、返回值**必须有**类型注解
- 使用 `typing` 模块（`List`, `Dict`, `Optional`, `Union`）
- 禁止裸 `Any`

```python
from typing import List, Optional

def submit_request(self, prompt: str, max_tokens: int) -> str:
    ...
```

---

## 5. 日志规范

- **模块顶部**：`logger = logging.getLogger(__name__)`
- **禁止**使用 `print()`（调试时允许 `print()`，提交前必须移除）
- 日志级别语义：
  - `DEBUG`：开发细节（输入参数、中间状态）
  - `INFO`：正常流程（请求开始/结束、批次触发）
  - `WARNING`：可恢复异常（KV Cache 命中率低、批次超时）
  - `ERROR`：需关注的错误（推理失败、OOM）

```python
logger.info("Request %s submitted to scheduler", request_id)
logger.warning("KV Cache hit rate below threshold: %.2f", hit_rate)
logger.error("Inference failed for request %s: %s", request_id, exc)
```

---

## 6. 错误处理

- **自定义异常**：每个模块可定义 `class XxxError(Exception)`（如 `KVCacheError`）
- **捕获异常**：记录完整上下文（request_id、模块名、关键参数）
- **不吞噬异常**：除非有明确理由，否则重新 `raise`
- **超时处理**：使用 `asyncio.timeout()` 或 `threading` 超时

---

## 7. 导入规范

```python
# 标准库
import logging
import time
from typing import List, Optional

# 第三方
import prometheus_client
import vllm

# 本地（使用相对导入）
from .inference_engine import InferenceEngine
from ..metrics_exporter import MetricsExporter
```

---

## 8. Docstring 规范

使用 Google Style：

```python
class InferenceEngine:
    """封装 vLLM 推理引擎的接口。

    提供同步/异步推理调用、metrics 回调注册等功能。

    Attributes:
        model_name: 模型名称。
        tp_size: 张量并行度。
    """

    def submit(self, request: InferenceRequest) -> str:
        """提交推理请求。

        Args:
            request: 推理请求对象。

        Returns:
            request_id: 唯一请求 ID，用于后续查询。

        Raises:
            InferenceError: 推理引擎内部错误。
        """
```

---

## 9. 禁止事项

| 禁止 | 替代 |
|------|------|
| `print()` 用于日志 | `logger.info()` |
| 裸 `Any` | 具体类型注解 |
| 全局可变状态 | 类属性或参数传递 |
| 魔法数 | 命名常量 |
| 跨模块循环导入 | 重构模块边界 |
| 提交无测试的新功能 | 同步提交 `*_test.py` |
| 直接 `except:` | `except SomeException:` |

---

## 10. 配置管理

- 所有可调参数必须来源于 `configs/*.yaml` 或环境变量
- **不得硬编码**任何 Magic Number（如 `chunk_size=512` 应来自配置）
- 使用 `PyYAML` 读取配置文件
- 配置变更通过调参接口（Mock）进行，不修改源码常量
