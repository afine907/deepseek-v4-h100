# 实验复现文档

> **状态**: ⚠️ 当前环境无 H100 GPU，数据来源说明：
> - **Mock 验证**: 基于 `MockInferenceEngine`（Tasks 1–7 完成）
> - **真实数据待填**: `Task 8` 需要 vLLM + GPU 环境，结果待实测后补充
> - **最终目标**: DeepSeek-V4-Flash 8×H100 推理结果

---

## 一、环境设置

### 1.1 硬件环境

- **H100 目标环境**: 8× NVIDIA H100 (80GB) + NVLink 全互联 + CUDA 12.x
- **当前开发环境**: WSL2 Ubuntu 22.04 (无 GPU)

### 1.2 软件环境

- Docker
- 镜像：`deepseek-v4-h100:latest`
- vLLM ≥ 0.4.0
- Python ≥ 3.10

### 1.3 构建镜像

```bash
docker build -t deepseek-v4-h100 .
```

### 1.4 当前开发环境验证命令（Mock 模式，无需 GPU）

```bash
# Mock adapter 验证（已完成）
python -m pytest tests/unit/ -v                    # 59/59 测试通过
python tests/benchmark_swe.py --adapter mock --output results.json --num-requests 100

# EvalPipeline 端到端验证（已完成）
python -c "
from pathlib import Path
from src.adapters.mock_adapter import MockInferenceEngine
from src.eval.pipeline import EvalPipeline
p = EvalPipeline(MockInferenceEngine(), {}, Path('output/eval'))
p.run(num_runs=2, num_requests=50)
"
```

---

## 二、基线运行（未优化）

### 2.1 启动基线服务

```bash
# H100 目标环境
bash launch_h100.sh \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90

# 开发环境 Mock 验证（无需 GPU）
python -m src.main --mode mock
```

### 2.2 运行 SWE-bench 评测

```bash
# 目标环境（需要 GPU）
python tests/benchmark_swe.py \
  --adapter vllm \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --output baseline_results.json \
  --num-requests 100

# 开发环境 Mock 验证
python tests/benchmark_swe.py \
  --adapter mock \
  --output baseline_results.json \
  --num-requests 100
```

### 2.3 基线性能数据

| 指标 | Mock 基线值 | 说明 |
|------|-------------|------|
| P50 延迟 | 0.525 s | MockInferenceEngine, 2 runs × 50 req 平均 |
| P90 延迟 | 0.806 s | 同上 |
| P99 延迟 | 1.063 s | 同上 |
| QPS | 36.3 | 同上 |
| GPU 利用率 | 0% | Mock 模式，无真实 GPU 占用 |
| KV Cache 命中率 | 0% | MockKVCacheManager 首轮无缓存历史 |
| SWE-bench 完成率 | — | 待 H100 环境实测 |

> **Mock 模式说明**: Mock 数据仅用于验证 EvalPipeline 逻辑正确性，不代表真实推理性能。Qwen3.5-0.8B 在 CPU 模式下 P50 通常为 2–10 s（取决于 token 数量）。

---

## 三、优化运行

### 3.1 启动优化服务

```bash
# H100 目标环境
bash launch_h100.sh \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90
```

### 3.2 运行 SWE-bench 评测

```bash
python tests/benchmark_swe.py \
  --adapter vllm \
  --model deepseek-v4-flash \
  --output optimized_results.json \
  --num-requests 100
```

### 3.3 优化性能数据（待实测）

| 指标 | 优化值 | 说明 |
|------|--------|------|
| P50 延迟 | ? s | 待 H100 实测 |
| P90 延迟 | ? s | 待 H100 实测 |
| P99 延迟 | ? s | 待 H100 实测 |
| QPS | ? | 待 H100 实测 |
| GPU 利用率 | ? % | 待 H100 实测 |
| KV Cache 命中率 | ? % | 待 H100 实测 |
| SWE-bench 完成率 | ? % | 待 H100 实测 |

---

## 四、性能对比

### 4.1 对比表（Mock 基线参考）

```
┌───────────────┬─────────────┬─────────────┬─────────┐
│ 指标           │ Mock 基线    │ 优化后       │ 提升    │
├───────────────┼─────────────┼─────────────┼─────────┤
│ P99 延迟       │ 1.06 s     │ ? s         │ ? %    │
│ QPS            │ 36.3       │ ?           │ ? %    │
│ GPU 利用率     │ 0% (Mock)  │ ? %         │ ? pp   │
│ KV Cache 命中率 │ 0%         │ ? %         │ ? pp   │
│ SWE-bench 完成率│ —          │ ? %         │ ? pp   │
└───────────────┴─────────────┴─────────────┴─────────┘
```

### 4.2 关键优化点效果分析

- **KV Cache LRU**: 对长尾请求的缓存命中效果（Mock 无历史，故命中率 0%）
- **Chunked Prefill**: 对长输入请求的延迟改善
- **Continuous Batching**: 对 QPS 和 GPU 利用率的提升

---

## 五、已知问题

- [x] Mock 验证完成（Tasks 1–7）
- [ ] vLLM CPU 模式验证（Task 8 — 需要 GPU 环境）
- [ ] DeepSeek-V4-Flash 模型权重获取方式待确认
- [ ] SWE-bench 数据集准备
- [ ] 8×H100 H100 真实环境 benchmark（最终目标）
