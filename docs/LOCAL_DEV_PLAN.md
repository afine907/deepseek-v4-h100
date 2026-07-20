# 本地开发环境方案（v2.1）

> **版本：** v2.1
> **日期：** 2026-07-19
> **状态：** 待执行
> **核心变化**：
> - ❌ 放弃 WSL2 CPU 模式（vLLM 竞态 Bug + warmup 问题无法解决）
> - ✅ 聚焦 Mock-first 开发 + Docker Compose 验证
> - ✅ 换用更小模型：`Qwen/Qwen2.5-0.5B-Instruct`

---

## 一、决策

| 决策 | 原因 |
|------|------|
| 放弃 WSL2 CPU | vLLM 0.25.1 在 WSL2 有 socket 竞态 Bug（PR #20275 未包含在 0.25.1），无 GPU 环境下 warmup 太慢 |
| Docker Compose 模式 | vLLM + OpenWebUI 同 Docker 网络互通，零端口转发问题 |
| Mock-first 开发 | 日常开发零依赖，秒级启动，核心调度逻辑可验证 |
| Qwen2.5-0.5B | 0.5B 参数，内存需求 ~1GB，vLLM CPU 可用，适合本地验证 |

---

## 二、执行计划

### Phase 0：验证 Mock 模式（立即可做）

```bash
cd d:/Code/deepseek-v4-h100

# 安装依赖
pip install -r requirements-dev.txt

# 运行单元测试
python -m pytest tests/unit/ -v --tb=short

# 运行 eval pipeline（Mock）
python -c "
from src.eval.pipeline import EvalPipeline
from src.adapters.mock_adapter import MockInferenceEngine
pipeline = EvalPipeline(
    adapter=MockInferenceEngine(),
    scheduler_config={'chunk_size': 512, 'prefill_ratio': 0.3}
)
print(pipeline.run(num_runs=1, num_requests=20))
"
```

**验证通过标准**：pytest 无失败，eval pipeline 输出 P50/P90/P99 数据。

---

### Phase 1：Docker Compose 验证

**目标**：在 WSL2 Docker 中运行 vLLM CPU + OpenWebUI，验证完整链路。

**前置**：
- WSL2 内 Docker 运行中
- 约 5GB 磁盘空间

**Step 1.1：更新 docker-compose.yml 模型**

```yaml
# 确认 docs/docker-compose.local.yml 中 vllm service 的 command 为：
command: >
  --model Qwen/Qwen2.5-0.5B-Instruct
  --host 0.0.0.0
  --port 8000
  --dtype bfloat16
  --max-model-len 512
  --enforce-eager
```

**Step 1.2：启动服务**

```bash
cd d:/Code/deepseek-v4-h100
docker compose -f docs/docker-compose.local.yml up -d

# 等待 healthcheck（约 1-3 分钟，首次下载模型）
docker compose -f docs/docker-compose.local.yml ps
```

**Step 1.3：验证**

```bash
# 验证 vLLM API
curl http://localhost:8000/v1/models

# 验证 OpenWebUI
curl http://localhost:8080

# 测试推理
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "messages": [{"role": "user", "content": "Hello"}],
    "max_tokens": 50
  }'
```

**Step 1.4：Windows 浏览器测试**

- OpenWebUI：`http://127.0.0.1:8080`
- 应能看到模型列表，可发送消息

**验证通过标准**：浏览器可对话，返回模型响应。

---

### Phase 2：端到端测试（Docker Compose）

**目标**：用 Docker Compose 环境跑完整的 eval pipeline。

**Step 2.1：更新 vllm_adapter 连接地址**

`src/adapters/vllm_adapter.py` 中 base_url 改为：
```python
base_url = "http://localhost:8000/v1"  # Windows/Git Bash 访问 WSL2 Docker
```

**Step 2.2：运行集成测试**

```bash
# 验证 vLLM 适配器
python -c "
from src.adapters.vllm_adapter import VLLMInferenceEngine
engine = VLLMInferenceEngine(base_url='http://localhost:8000/v1')
print(engine.get_status())
"
```

**Step 2.3：停止服务**

```bash
docker compose -f docs/docker-compose.local.yml down
```

---

## 三、回滚方案

| 操作 | 回滚 |
|------|------|
| Docker Compose 启动 | `docker compose -f docs/docker-compose.local.yml down -v` |
| vllm_adapter 修改 | `git checkout src/adapters/vllm_adapter.py` |
| 任何时刻重置 | `cd d:/Code/deepseek-v4-h100 && git checkout .` |

---

## 四、验证清单

```
[ ] Phase 0: pytest tests/unit/ 无失败
[ ] Phase 0: eval pipeline 输出 P50/P90/P99
[ ] Phase 1: docker compose ps 显示两服务 healthy
[ ] Phase 1: curl localhost:8000/v1/models 返回 JSON
[ ] Phase 1: 浏览器 http://127.0.0.1:8080 可打开
[ ] Phase 1: 浏览器中发送消息，模型返回响应
[ ] Phase 2: vLLM 适配器可查询状态
```

---

## 五、模型对比

| 模型 | 参数量 | 内存需求 | 特点 |
|------|--------|---------|------|
| Qwen/Qwen2.5-0.5B-Instruct | 0.5B | ~1GB | ✅ 推荐，vLLM 官方支持，CPU 可用 |
| Qwen/Qwen3-0.8B | 0.8B | ~1.5GB | vLLM 支持，非 VL |
| Qwen/Qwen3.5-0.8B | 0.8B | ~2GB | ❌ 含 VL 编码器，warmup 太慢 |

---

## 六、文件变更

| 文件 | 变更 |
|------|------|
| `docs/docker-compose.local.yml` | 更新模型为 `Qwen/Qwen2.5-0.5B-Instruct` |
| `docs/LOCAL_DEV_PLAN.md` | 更新模型信息，移除 WSL2 CPU 模式 |
| `docs/DEVELOPMENT_COMMANDS.md` | 更新 Phase 1 启动命令 |
