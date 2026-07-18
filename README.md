# DeepSeek-V4-Flash 8×H100 推理优化系统

> 面向 SWE-bench 的端到端推理性能优化系统

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## 📋 目录

- [项目概述](#项目概述)
- [架构](#架构)
- [快速开始](#快速开始)
- [核心优化](#核心优化)
- [配置参数](#配置参数)
- [项目结构](#项目结构)
- [文档](#文档)

---

## 项目概述

本系统面向 **AI Coding 场景下的大模型在线推理服务**，在 8×H100 集群上完成 DeepSeek-V4-Flash 的部署与性能优化，并在 SWE-bench 工作负载下完成端到端验证。

### 核心挑战

- 长上下文显存压力（代码仓库级依赖）
- 延迟抖动（长尾分布 + 突发流量）
- GPU 利用率低（Prefill/Decode 互相等待）
- OOM 风险（长请求堆叠）

### 优化目标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| P99 延迟 | 10.0 s | < 5.0 s |
| QPS | 50 | > 100 |
| GPU 利用率 | 50% | > 80% |
| KV Cache 命中率 | 40% | > 70% |
| SWE-bench 完成率 | 95% | > 99% |

> ⚠️ 基线为假设值，待实测后校准。详见 [docs/brainstorming/05-metrics-assumption.md](docs/brainstorming/05-metrics-assumption.md)

---

## 架构

### 四层架构

```
控制层（Auto-Tuner）
         ↓
路由与调度层（Chunked Prefill + Continuous Batching）
         ↓
推理引擎层（vLLM / FP8 / TP=8）
         ↓
可观测层（Prometheus Metrics）
```

详见 [docs/competition-document.md](docs/competition-document.md)

### 架构图

| 图 | 说明 |
|----|------|
| [四层架构总览](docs/srs/figures/architecture-diagrams.md#图-1四层架构总览) | 控制/调度/引擎/可观测四层 |
| [请求处理时序](docs/srs/figures/architecture-diagrams.md#图-2请求处理时序) | 请求从入口到响应的完整链路 |
| [LRU 淘汰流程](docs/srs/figures/architecture-diagrams.md#图-3lru-淘汰流程) | KV Cache 显存保护机制 |
| [TP=8 分布式架构](docs/srs/figures/architecture-diagrams.md#图-4tp8-分布式架构) | 8×H100 NVLink 集群 |
| [Continuous Batching 调度](docs/srs/figures/architecture-diagrams.md#图-5continuous-batching-调度) | 迭代级批处理示意 |

---

## 快速开始

### 环境要求

- Docker
- 8× NVIDIA H100 (80GB)
- CUDA 12.x
- Python 3.10+

### 构建镜像

```bash
docker build -t deepseek-v4-h100 .
```

### 启动服务

```bash
# 基本启动
bash launch_h100.sh \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90

# 查看完整参数
bash launch_h100.sh --help
```

### 本地开发（无 GPU 环境）

```bash
# 安装依赖
pip install -r requirements-dev.txt

# 运行 Mock 测试
pytest tests/ -m mock

# 运行单元测试
pytest tests/unit/
```

---

## 核心优化

### 1. KV Cache LRU 淘汰

防止长上下文显存溢出，与 SWE-bench 长尾分布局部性匹配。

- 触发条件：显存 > 90%
- 淘汰粒度：Block-level
- 参考：[docs/brainstorming/02-kv-cache-lfu.md](docs/brainstorming/02-kv-cache-lfu.md)

### 2. Chunked Prefill

将长输入切分为 512 tokens/块，消除长尾请求对 Decode 阶段的阻塞。

- chunk_size：512 tokens
- prefill_ratio：0.3
- 反饥饿：SJF + aging 机制
- 参考：[docs/brainstorming/03-chunked-prefill-assumption.md](docs/brainstorming/03-chunked-prefill-assumption.md)

### 3. Continuous Batching

迭代级批处理，最大化 GPU 利用率。

- 不使用 Micro-Batching（TP=8 + MoE All-to-All overhead 考量）
- max_batch_size：32
- 参考：[docs/brainstorming/06-tp8-nccl.md](docs/brainstorming/06-tp8-nccl.md)

### 4. TP=8 张量并行

8×H100 NVLink 全互联，NCCL 调参优化。

- 参考：[docs/brainstorming/06-tp8-nccl.md](docs/brainstorming/06-tp8-nccl.md)

---

## 配置参数

| 参数 | 值 | 说明 |
|------|---|------|
| `kv_cache.淘汰策略` | LRU | KV Cache 淘汰 |
| `kv_cache.high_watermark` | 0.90 | 触发淘汰的显存水位 |
| `kv_cache.low_watermark` | 0.75 | 停止淘汰的显存水位 |
| `chunked_prefill.chunk_size` | 512 | tokens/块 |
| `chunked_prefill.max_chunks_per_request` | 64 | 单请求最大块数 |
| `batching.prefill_ratio` | 0.3 | prefill 占比上限 |
| `batching.max_batch_size` | 32 | 单批最大请求数 |
| `batching.max_wait_time_ms` | 100 | 凑批超时 |
| `model.tensor_parallel_size` | 8 | 张量并行度 |
| `model.quantization` | FP8 | 量化精度 |

详细配置见 `configs/` 目录。

---

## 项目结构

```
deepseek-v4-h100/
├── Dockerfile                  # 容器镜像构建
├── launch_h100.sh            # 一键启动脚本
├── configs/                   # 配置文件
│   ├── model.yaml
│   ├── batching.yaml
│   └── kv_cache.yaml
├── src/                       # 源代码
│   ├── scheduler.py           # 调度层（Chunked Prefill）
│   ├── kv_cache_manager.py    # KV Cache LRU 管理
│   ├── inference_engine.py    # vLLM 引擎封装
│   ├── metrics_exporter.py    # Prometheus 指标
│   └── control/
│       └── auto_tuner.py      # 自动调优
├── tests/                     # 测试
│   ├── unit/                  # 单元测试
│   ├── integration/            # 集成测试
│   └── benchmark_*.py         # SWE-bench 评测脚本
├── docs/                      # 文档
│   ├── srs/                   # 系统需求规格
│   │   ├── SRS-00-draft.md
│   │   └── figures/           # 架构图
│   ├── brainstorming/         # 决策记录
│   ├── competition-document.md # 参赛文档
│   └── original-requirements.md
└── README.md                  # 本文件
```

---

## 文档

| 文档 | 说明 |
|------|------|
| [docs/competition-document.md](docs/competition-document.md) | 参赛文档（核心） |
| [docs/srs/SRS-00-draft.md](docs/srs/SRS-00-draft.md) | 系统需求规格说明书 |
| [docs/srs/figures/architecture-diagrams.md](docs/srs/figures/architecture-diagrams.md) | 架构图集（Mermaid） |
| [docs/brainstorming/](docs/brainstorming/) | 决策过程记录 |

---

## 开发说明

### 本地开发（无 GPU）

```bash
# 克隆到本地后
cd deepseek-v4-h100

# 使用 Claude Code 开发
claude

# 或直接运行测试
pytest tests/unit/ -v
```

### 提交代码

```bash
git checkout -b feature/xxx
# ... 编码 ...
git add .
git commit -m "feat: xxx"
git push origin feature/xxx
# 然后提 PR
```

---

## License

MIT
