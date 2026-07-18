# 测试目录

> ⏳ 本目录所有文件为占位符，将在开发阶段逐步实现。

## 测试结构

| 目录/文件 | 说明 | 状态 |
|---------|------|------|
| `unit/` | 单元测试 | ⏳ 待实现 |
| `integration/` | 集成测试 | ⏳ 待实现 |
| `benchmark_swe.py` | SWE-bench 评测脚本 | ⏳ 待实现 |
| `conftest.py` | pytest 配置 | ⏳ 待实现 |

## 测试命令

```bash
# 运行单元测试
pytest tests/unit/ -v

# 运行 Mock 测试（无 GPU 环境）
pytest tests/ -m mock

# 运行 SWE-bench 基准评测
python tests/benchmark_swe.py --output results.json

# 查看指标
curl http://localhost:8000/metrics
```

## Mock 测试说明

无 GPU 环境下，使用 `MockInferenceEngine`（定义于 `docs/brainstorming/04-api-contracts.md`）模拟 vLLM 返回：
- 模拟延迟：100~2000ms 随机
- 模拟生成 token 数：50~500 随机

## 标签

| 标签 | 用途 |
|------|------|
| `mock` | 无 GPU 的 Mock 测试 |
| `unit` | 单元测试 |
| `integration` | 集成测试 |
| `benchmark` | 性能基准测试 |
