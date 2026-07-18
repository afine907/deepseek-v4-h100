# AI_AGENT_ONBOARDING.md — AI Agent 首次上手

> 本文件是 AI Agent（如 Claude Code、Cursor、Windsurf 等）首次接触本仓库时的上手指南。

---

## 首次会话 Checklist

- [ ] 阅读 [AGENTS.md](../AGENTS.md) 整体索引
- [ ] 阅读 [docs/PRODUCT_SPEC.md](PRODUCT_SPEC.md) 理解系统定位
- [ ] 阅读 [docs/ARCHITECTURE.md](ARCHITECTURE.md) 理解四层架构
- [ ] 阅读 [docs/STANDARDS.md](STANDARDS.md) 了解编码规范
- [ ] 阅读 [docs/TESTING_GUIDE.md](TESTING_GUIDE.md) 了解测试要求
- [ ] 阅读 [docs/DEVELOPMENT_COMMANDS.md](DEVELOPMENT_COMMANDS.md) 了解可用命令

---

## 快速上手

### 1. 环境准备

```bash
# 克隆仓库（如未克隆）
git clone <repo-url>
cd deepseek-v4-h100

# 安装开发依赖（无 GPU 也可）
pip install -r requirements-dev.txt
```

### 2. 验证安装

```bash
# 运行 Mock 测试（无 GPU 环境）
pytest tests/ -m mock -v

# 确认测试通过
# 应看到所有 test_scheduler、test_kv_cache_manager 等测试 PASSED
```

### 3. 理解核心模块

按以下顺序阅读源码（从依赖最少到最多）：

```
metrics_exporter.py     → inference_engine.py → scheduler.py → kv_cache_manager.py
（无依赖）              （依赖 metrics）        （依赖 engine）  （与 scheduler 交互）
```

详细模块文档见：
- [src/metrics_exporter.md](../src/metrics_exporter.md)
- [src/inference_engine.md](../src/inference_engine.md)
- [src/scheduler.md](../src/scheduler.md)
- [src/kv_cache_manager.md](../src/kv_cache_manager.md)
- [src/control/tuner_interface.md](../src/control/tuner_interface.md)

---

## 架构要点

### 调度层（scheduler.py）是核心

`scheduler.py` 是整个系统的调度中枢：
- 接收 HTTP/gRPC 请求
- 执行 Chunked Prefill（分块）
- 管理 Continuous Batching（批处理）
- 分发到 vLLM

修改调度逻辑前，必须先理解：
1. `InferenceRequest` / `InferenceResponse` 数据结构
2. `ChunkedPrefillState` 状态机
3. `ContinuousBatchingPolicy` 策略

### KV Cache 管理与 vLLM 交互

`kv_cache_manager.py` 直接与 vLLM 的 block 分配系统交互。
**不要**在不了解 vLLM block API 的情况下修改 LRU 淘汰逻辑。

### 配置优先

所有可调参数必须通过 `configs/*.yaml` 或 `update_config()` 接口修改。
**不得硬编码** Magic Number。

---

## 开发流程

1. 从 [AGENTS.md](../AGENTS.md) 的 "Quick Commands" 选择合适的测试命令
2. 使用 `pytest tests/ -m mock -v` 快速验证逻辑（无 GPU）
3. 先写测试，再写实现（TDD）
4. commit 使用 Conventional Commits 格式

---

## 常见问题

### Q: 没有 GPU 能开发吗？

**能。** 使用 Mock 测试即可验证大部分逻辑：

```bash
pytest tests/ -m mock -v
```

MockInferenceEngine 模拟 vLLM 的行为（随机延迟 100~2000ms）。

### Q: 需要了解 DeepSeek-V4-Flash 模型本身吗？

**不需要。** vLLM 已经封装了模型调用细节，你只需要关注调度逻辑。

### Q: 配置文件在哪里？

`configs/` 目录，包含：
- `model.yaml` — 模型参数
- `batching.yaml` — 批处理参数
- `scheduler.yaml` — 调度参数
- `kv_cache.yaml` — KV Cache 参数

### Q: 测试失败怎么办？

1. 检查是否缺少依赖：`pip install -r requirements-dev.txt`
2. 查看具体错误信息
3. 如果是 Mock 相关测试，确保使用了 `-m mock` 标记
4. 确认代码没有引入与 vLLM API 不兼容的变更

---

## 参考资料

- vLLM 文档：https://docs.vllm.ai/
- Prometheus client：https://prometheus.io/docs/instrumenting/clientlibs/python/
- DeepSeek-V4-Flash 模型卡（待补充）
