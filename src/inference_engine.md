# inference_engine.py — vLLM 引擎封装

> ⏳ 本模块为占位符，待实现。

---

## 模块职责

`inference_engine.py` 封装 vLLM 的 Python API，提供：
1. **LLM 实例管理** — TP=8, FP8, gpu_memory_utilization=0.90
2. **同步/异步推理调用** — `submit()` + `get_result()`
3. **错误处理** — OOM、超时、vLLM 异常
4. **Metrics 回调** — 注册推理指标回调

---

## 公开接口

```python
class InferenceEngine:
    """封装 vLLM 推理引擎。"""

    def __init__(
        self,
        model_name: str = "deepseek-v4-flash",
        tensor_parallel_size: int = 8,
        gpu_memory_utilization: float = 0.90,
        quantization: str = "FP8",
        **kwargs,
    ):
        """初始化 vLLM LLM 实例。"""

    def submit(self, request: InferenceRequest) -> str:
        """提交推理请求，返回 request_id。"""

    def get_result(self, request_id: str) -> InferenceResponse | None:
        """非阻塞获取结果。"""

    def get_stats(self) -> EngineStats:
        """获取引擎统计信息。"""


@dataclass
class EngineStats:
    total_requests: int
    running_requests: int
    avg_latency_ms: float
```

---

## vLLM 初始化（预期代码）

```python
from vllm import LLM, SamplingParams

self.llm = LLM(
    model=model_name,
    tensor_parallel_size=tensor_parallel_size,
    gpu_memory_utilization=gpu_memory_utilization,
    quantization=quantization,
    trust_remote_code=True,
)

self.sampling_params = SamplingParams(
    temperature=request.temperature,
    max_tokens=request.max_tokens,
)
```

---

## Mock 模式（无 GPU）

当无 GPU 或 `use_mock=True` 时，使用 `MockInferenceEngine`：

```python
# docs/brainstorming/04-api-contracts.md 中的 Mock 实现
class MockInferenceEngine:
    def submit(self, request: InferenceRequest) -> str:
        time.sleep(random.uniform(0.1, 2.0))
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

## 配置参数（来源：configs/model.yaml）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `model.name` | `deepseek-v4-flash` | 模型名称 |
| `model.tensor_parallel_size` | 8 | 张量并行度 |
| `model.quantization` | FP8 | 量化精度 |
| `model.gpu_memory_utilization` | 0.90 | GPU 显存利用率 |
| `model.max_seq_len` | 32768 | 最大序列长度 |

---

## 依赖关系

```
inference_engine.py
├── vllm（第三方库）
└── metrics_exporter.py（记录推理指标）
```

---

## Metrics（由 metrics_exporter.py 暴露）

| 指标 | 类型 | 说明 |
|------|------|------|
| `inference_requests_total` | Counter | 总请求数 |
| `inference_requests_failed_total` | Counter | 失败请求数 |
| `inference_latency_ms` | Histogram | 推理延迟分布 |
| `prefill_latency_ms` | Histogram | Prefill 延迟 |
| `decode_latency_ms` | Histogram | Decode 延迟 |
| `time_to_first_token_ms` | Histogram | TTFT |

---

## 测试

```bash
# Mock 测试（无 GPU）
pytest tests/ -m mock -v

# MockInferenceEngine 测试
pytest tests/mock/test_mock_inference.py -v
```

---

## 状态

⏳ **待实现** — 接口定义见 [docs/brainstorming/04-api-contracts.md](../docs/brainstorming/04-api-contracts.md)
