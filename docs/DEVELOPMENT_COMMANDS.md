# DEVELOPMENT_COMMANDS.md — 开发命令参考

> 所有命令在项目根目录（`deepseek-v4-h100/`）下执行。

---

## 依赖安装

### 本地开发环境（无 GPU）

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 验证安装
pip list | grep -E "pytest|prometheus-client|grpcio"
```

---

## 测试命令

```bash
# 运行所有测试（含详细输出）
pytest tests/ -v

# 仅 Mock 测试（无 GPU）
pytest tests/ -m mock -v

# 仅单元测试
pytest tests/unit/ -v

# 仅集成测试（需 GPU）
pytest tests/integration/ -v

# 运行特定文件
pytest tests/unit/test_scheduler.py -v

# 运行带覆盖率报告
pytest tests/ --cov=src --cov-report=term-missing

# 在第一个失败时停止
pytest tests/ -x

# 仅运行上次失败的测试
pytest tests/ --lf
```

---

## Docker 命令

```bash
# 构建镜像（需 GPU）
docker build -t deepseek-v4-h100 .

# 查看镜像
docker images | grep deepseek-v4-h100

# 运行容器（需 8×H100）
docker run --gpus '"device=0,1,2,3,4,5,6,7"' \
  -p 8000:8000 \
  --shm-size=64g \
  deepseek-v4-h100

# 进入容器 shell
docker run --gpus all -it deepseek-v4-h100 bash
```

---

## 推理服务启动

```bash
# 基本启动（需 8×H100）
bash launch_h100.sh \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90

# 自定义端口
bash launch_h100.sh --port 9000

# 查看帮助
bash launch_h100.sh --help

# 查看日志（容器内）
docker logs -f <container_id>
```

---

## SWE-bench 评测

```bash
# 运行 SWE-bench 评测（需 GPU + 推理服务运行）
python tests/benchmark_swe.py --output results.json

# 查看 results.json 格式
# 字段：request_id, prompt, generated_text, latency_ms, tokens_generated, pass
```

---

## Metrics 观测

```bash
# 推理服务运行后，查看 Prometheus metrics
curl http://localhost:8000/metrics

# 或在浏览器打开
open http://localhost:8000/metrics
```

---

## 代码质量

```bash
# 格式化代码（本项目使用 Black）
black src/ tests/

# 检查导入排序
isort src/ tests/

# 运行所有质量检查（需先安装）
ruff check src/
mypy src/
```

> ⚠️ `ruff`、`black`、`isort`、`mypy` 未在 `requirements-dev.txt` 中列出，
> 如需使用请单独安装：`pip install ruff black isort mypy`

---

## Git 工作流

```bash
# 创建分支
git checkout -b feature/scheduler-chunked-prefill

# 查看变更
git diff

# 暂存并提交
git add src/scheduler.py tests/unit/test_scheduler.py
git commit -m "feat(scheduler): 实现 Chunked Prefill 分块逻辑"

# 推送到远程
git push origin feature/scheduler-chunked-prefill
```

---

## 配置文件参考

| 文件 | 说明 |
|------|------|
| `configs/model.yaml` | 模型名称、TP 大小、量化方式、显存利用率 |
| `configs/batching.yaml` | 最大批次、超时时间、prefill 占比 |
| `configs/scheduler.yaml` | chunk 大小、最大块数 |
| `configs/kv_cache.yaml` | 淘汰策略、高低水位 |

修改配置后需重启推理服务生效。
