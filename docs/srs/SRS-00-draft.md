# 系统需求规格说明书 (SRS)

> **状态：** 🟡 草案 · 待最终确定
> **版本：** v0.1
> **日期：** 2026-07-18
> **项目：** DeepSeek-V4-Flash 8×H100 推理优化系统

---

## 变更记录

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 0.1 | 2026-07-18 | 初始草稿，建立文档结构 | jojo |

---

## 目录

1. [引言](#1-引言)
2. [总体描述](#2-总体描述)
3. [具体需求](#3-具体需求)
4. [附录](#4-附录)

---

## 1. 引言

### 1.1 目的

本系统需求规格说明书（SRS）旨在完整定义 **DeepSeek-V4-Flash 8×H100 推理优化系统** 的功能需求、性能需求、接口需求及交付标准。

本书面需求将作为：
- 工程实现的验收依据
- 参赛文档的核心章节
- 评测对比的基线参照

### 1.2 范围

本系统面向 **公司内 AI Coding 场景下的大模型在线推理服务**，核心目标：

1. 在 8×H100 集群上完成 DeepSeek-V4-Flash 的稳定部署
2. 在 SWE-bench 工作负载下完成系统级性能验证
3. 交付可直接复现的工程化方案

**不在本系统范围内：**
- 模型训练与微调
- 前端应用界面开发
- 非 Docker 部署方式
- 跨集群分布式部署

### 1.3 定义与缩略语

| 术语 | 全称 | 说明 |
|------|------|------|
| TP | Tensor Parallelism | 张量并行，将单层权重切分到多卡 |
| DP | Data Parallelism | 数据并行，多请求并行处理 |
| MoE | Mixture of Experts | 混合专家模型（DeepSeek-V4 架构） |
| FP8 | 8-bit Floating Point | 8位浮点量化 |
| Prefill | Prefill Phase | 首次推理阶段，处理输入 prompt |
| Decode | Decode Phase | 自回归解码阶段，生成 token |
| KV Cache | Key-Value Cache | 注意力机制的键值缓存 |
| Chunked Prefill | 分块预填充 | 将长输入切分为小块，防止阻塞 |
| SWE-bench | Software Engineering Benchmark | 软件工程任务评测基准 |

### 1.4 参考资料

- [ ] DeepSeek-V4-Flash 官方技术文档
- [ ] vLLM 官方文档
- [ ] NVIDIA H100 产品规格书
- [ ] SWE-bench 官方 GitHub

---

## 2. 总体描述

### 2.1 系统边界

本系统为 **端到端推理服务系统**，包含以下四层架构：

```
┌─────────────────────────────────────────────┐
│  控制层 / Agent（调参接口）← 2周版：Mock/预留，不启用实时闭环 │
├─────────────────────────────────────────────┤
│  推理引擎层（vLLM / FP8 / TP=8）            │  ← 核心层
├─────────────────────────────────────────────┤
│  路由与调度层（Chunked Prefill / Batching）  │  ← 核心层
├─────────────────────────────────────────────┤
│  可观测层（Prometheus Metrics）              │  ← 指标采集
└─────────────────────────────────────────────┘
```

**决策记录（详见 `docs/brainstorming/`）：**
- ✅ 控制层自动调优砍掉（参赛版不实现），预留接口/Mock。实时闭环不在4小时赛程范围内。
- ✅ KV Cache 淘汰策略：LRU
- ✅ Chunked Prefill chunk_size：假设 512 tokens（待基线实测校准）
- ✅ 接口协议：gRPC（进程内调用，不做 Streaming）
- ✅ 批处理：Continuous Batching + 等待结束再插入，prefill_ratio=0.3
- ✅ TP=8 + NCCL 调参，不做自定义 routing
- ❌ Speculative Decoding：不做
- ⚠️ Nsight Systems：降级为文档说明，容器内不安装

### 2.2 用户特征

| 角色 | 描述 |
|------|------|
| 参赛选手 | 使用系统进行评测、对比实验 |
| 内部开发者 | 使用系统进行 AI Coding 推理服务 |
| 运维工程师 | 部署、监控、问题排查 |

### 2.3 约束条件

| 约束类型 | 具体内容 |
|---------|---------|
| 硬件约束 | 8× NVIDIA H100 (80GB) 集群 |
| 软件约束 | Docker 容器化，CUDA 12.x + PyTorch + vLLM |
| 量化约束 | FP8 精度 |
| 评测约束 | SWE-bench 数据集 |

### 2.4 假设与依赖

- [ ] 8×H100 集群环境可用
- [ ] DeepSeek-V4-Flash 模型权重可获取
- [ ] vLLM 已支持 DeepSeek-V4-Flash FP8 量化
- [ ] SWE-bench 数据集已准备完毕

---

## 3. 具体需求

> ⏳ **待填充** — 头脑风暴后逐节完善

### 3.1 功能需求

#### 3.1.1 KV Cache 管理

| 功能 | 规格 |
|------|------|
| 淘汰策略 | LRU（Least Recently Used） |
| 淘汰触发 | 显存使用率 > 高水位（默认 90%），或可用 block < 最低阈值 |
| 淘汰粒度 | Block-level |

**参考：** `docs/brainstorming/02-kv-cache-lfu.md`（⚠️ 文件名 `lfu` 为历史遗留，内容为 LRU）（⚠️ 文件名 `lfu` 为历史遗留，内容为 LRU）

#### 3.1.2 Chunked Prefill 调度

| 功能 | 规格 |
|------|------|
| chunk_size | 512 tokens（假设值，待实测校准） |
| 最大 chunk 数/请求 | 64 |
| 反饥饿机制 | SJF + aging（Shortest Job First + 等待时间衰减） |
| prefill credit budget | 2（每次最多占用的 token budget） |

**参考：** `docs/brainstorming/03-chunked-prefill-assumption.md`

#### 3.1.3 批处理调度

| 功能 | 规格 |
|------|------|
| 批处理模式 | Continuous Batching（在解码迭代边界插入，非等到 batch 完全空闲） |
| max_batch_size | 32 |
| prefill_ratio | 0.3（保守，防长请求霸占 GPU） |
| max_wait_time_ms | 100ms（凑批超时，强制执行） |
| Micro-Batching | 不启用（TP=8 + MoE All-to-All 场景下 overhead 大） |

**参考：** `docs/brainstorming/06-tp8-nccl.md`

#### 3.1.4 张量并行（TP=8）

| 功能 | 规格 |
|------|------|
| 并行策略 | TP=8（张量并行 8 卡） |
| 通信优化 | NCCL 环境变量调参 |
| 负载均衡 | vLLM MoE 默认负载均衡（需确认开启） |

**参考：** `docs/brainstorming/06-tp8-nccl.md`

#### 3.1.5 推理引擎

| 功能 | 规格 |
|------|------|
| 框架 | vLLM（DeepSeek-V4-Flash 官方适配版） |
| 量化精度 | FP8 |
| 张量并行 | TP=8 |
| 批处理 | 动态连续批处理（Continuous Batching） |

#### 3.1.6 控制层接口（预留/Mock）

| 功能 | 规格 |
|------|------|
| 接口 | 手动调参接口（Mock 实现） |
| 调参范围 | batch_size, chunk_size, kv_cache_high_watermark |
| 调参方式 | 人工触发（参赛版不启用实时闭环） |

**参考：** `docs/brainstorming/01-scope.md`

### 3.2 性能需求

> ⚠️ 以下为假设值，待基线实测后校准。真实数据见 `docs/brainstorming/05-metrics-assumption.md`

#### 3.2.1 延迟指标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| P50 延迟 | 1.5 s | < 1.0 s |
| P90 延迟 | 5.0 s | < 3.0 s |
| P99 延迟 | 10.0 s | < 5.0 s |

#### 3.2.2 吞吐指标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| QPS | 50 | > 100 |
| GPU 利用率 | 50% | > 80% |

#### 3.2.3 显存指标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| KV Cache 命中率 | 40% | > 70% |
| 显存峰值占用 | 75 GB | < 70 GB |

#### 3.2.4 评测指标

| 指标 | 目标 |
|------|------|
| SWE-bench 请求完成率 | > 99% |
| 超时率（30s阈值） | < 1% |

### 3.3 接口需求

#### 3.3.1 控制层 ↔ 调度层

| 项目 | 内容 |
|------|------|
| 协议 | **gRPC** |
| 功能 | 调参指令下发、状态查询 |
| 参数 | batch_size, chunk_size, kv_cache_watermark, max_concurrent_requests |
| Streaming | **不做** |
| 参考 | `docs/brainstorming/04-api-contracts.md` |

#### 3.3.2 调度层 ↔ 推理引擎层

| 项目 | 内容 |
|------|------|
| 协议 | **Python 函数调用（进程内）** |
| 核心接口 | submit() / get_result() / cancel() / get_queue_status() |
| 数据格式 | InferenceRequest / InferenceResponse（见 04-api-contracts.md） |

#### 3.3.3 推理引擎层 → 可观测层

| 项目 | 内容 |
|------|------|
| 协议 | Prometheus Pushgateway 或 OpenTelemetry |
| 暴露指标 | 延迟直方图 / 吞吐量计数 / GPU 显存仪表 / KV Cache 命中率 |
| 参考 | `docs/brainstorming/04-api-contracts.md` §3

### 3.4 可观测性需求

| 类型 | 指标 | 说明 |
|------|------|------|
| 延迟 | inference_latency_ms, prefill_latency_ms, decode_latency_ms, ttft_ms | Histogram |
| 吞吐 | requests_total, requests_failed_total, tokens_generated_total | Counter |
| 显存 | gpu_memory_used_bytes, kv_cache_blocks_used | Gauge（按 gpu_id 分 labels） |
| 缓存 | kv_cache_hit_rate | Gauge |
| 队列 | queue_length, active_requests | Gauge |
| 事件 | kv_cache_evicted_total, oom_events_total | Counter |

**暴露方式：** `/metrics` 端点，Prometheus 抓取格式

**参考：** `docs/brainstorming/04-api-contracts.md` §3

### 3.5 容错与自愈需求

| 功能 | 规格 |
|------|------|
| 防 OOM | KV Cache LRU 淘汰（>90% 触发）+ 单请求显存预算限制 |
| 防长尾抖动 | Chunked Prefill + prefill_ratio=0.3 限制 |
| 超时保护 | 单请求 30s 强制 kill |
| 健康检查 | `/health` 端点（vLLM 内置） |
| 自动重启 | 交由容器基础设施（Docker/k8s），代码层不做 |

**参考：** `docs/brainstorming/02-kv-cache-lfu.md`（⚠️ 文件名 `lfu` 为历史遗留，内容为 LRU）

### 3.6 交付物需求

| # | 交付物 | 文件 |
|---|--------|------|
| 1 | Docker 镜像 | `Dockerfile` |
| 2 | 启动脚本 | `launch_h100.sh` |
| 3 | 核心优化代码 | `src/kv_cache_manager.py`, `src/scheduler.py` |
| 4 | Prometheus 指标 | `src/metrics_exporter.py` |
| 5 | 调参接口（Mock 预留） | `src/control/tuner_interface.py` |
| 6 | 评测脚本 | `tests/benchmark_*.py` |
| 7 | 实验复现文档 | `docs/REPRODUCTION.md` |
| 8 | 项目说明 | `README.md` |

**一键启动验证：** `bash launch_h100.sh --model deepseek-v4-flash --tensor-parallel-size 8`

---

## 4. 附录

### 4.1 头脑风暴记录

| 文件 | 内容 | 状态 |
|------|------|------|
| `docs/brainstorming/01-scope.md` | Scope 边界 + 2周时间评估 | ✅ |
| `docs/brainstorming/02-kv-cache-lfu.md` | KV Cache LRU 淘汰策略 | ✅ |
| `docs/brainstorming/03-chunked-prefill-assumption.md` | Chunked Prefill chunk_size=512 | ✅ |
| `docs/brainstorming/04-api-contracts.md` | 接口契约（gRPC/进程内） | ✅ |
| `docs/brainstorming/05-metrics-assumption.md` | 量化指标假设 | ✅ |
| `docs/brainstorming/06-tp8-nccl.md` | TP=8 + 批处理策略 | ✅ |
| `docs/brainstorming/07-batching-strategy.md` | 批处理策略（合并至 06） | ✅ |

### 4.2 项目结构

```
deepseek-v4-h100/
├── docs/
│   ├── srs/
│   │   ├── SRS-00-draft.md      ← 当前文件
│   │   ├── figures/            ← 架构图、时序图
│   │   └── SRS-01-final.md     ← 定稿版（头脑风暴结束后）
│   ├── brainstorming/         ← 决策过程记录
│   └── original-requirements.md ← 原始需求归档
├── src/                       ← 代码（头脑风暴后创建）
├── configs/                   ← 配置文件
├── scripts/                   ← 启动脚本
├── tests/                     ← 评测脚本
└── README.md
```


| 功能 | 规格 |
|------|------|
| 接口 | 手动调参接口（Mock 实现） |
| 调参范围 | batch_size, chunk_size, kv_cache_high_watermark |
| 调参方式 | 人工触发（参赛版不启用实时闭环） |

**参考：** `docs/brainstorming/01-scope.md`

### 3.2 性能需求

> ⚠️ 以下为假设值，待基线实测后校准。真实数据见 `docs/brainstorming/05-metrics-assumption.md`

#### 3.2.1 延迟指标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| P50 延迟 | 1.5 s | < 1.0 s |
| P90 延迟 | 5.0 s | < 3.0 s |
| P99 延迟 | 10.0 s | < 5.0 s |

#### 3.2.2 吞吐指标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| QPS | 50 | > 100 |
| GPU 利用率 | 50% | > 80% |

#### 3.2.3 显存指标

| 指标 | 基线（假设） | 优化目标 |
|------|------------|---------|
| KV Cache 命中率 | 40% | > 70% |
| 显存峰值占用 | 75 GB | < 70 GB |

#### 3.2.4 评测指标

| 指标 | 目标 |
|------|------|
| SWE-bench 请求完成率 | > 99% |
| 超时率（30s阈值） | < 1% |

### 3.3 接口需求

#### 3.3.1 控制层 ↔ 调度层

| 项目 | 内容 |
|------|------|
| 协议 | **gRPC** |
| 功能 | 调参指令下发、状态查询 |
| 参数 | batch_size, chunk_size, kv_cache_watermark, max_concurrent_requests |
| Streaming | **不做** |
| 参考 | `docs/brainstorming/04-api-contracts.md` |

#### 3.3.2 调度层 ↔ 推理引擎层

| 项目 | 内容 |
|------|------|
| 协议 | **Python 函数调用（进程内）** |
| 核心接口 | submit() / get_result() / cancel() / get_queue_status() |
| 数据格式 | InferenceRequest / InferenceResponse（见 04-api-contracts.md） |

#### 3.3.3 推理引擎层 → 可观测层

| 项目 | 内容 |
|------|------|
| 协议 | Prometheus Pushgateway 或 OpenTelemetry |
| 暴露指标 | 延迟直方图 / 吞吐量计数 / GPU 显存仪表 / KV Cache 命中率 |
| 参考 | `docs/brainstorming/04-api-contracts.md` §3

### 3.4 可观测性需求

| 类型 | 指标 | 说明 |
|------|------|------|
| 延迟 | inference_latency_ms, prefill_latency_ms, decode_latency_ms, ttft_ms | Histogram |
| 吞吐 | requests_total, requests_failed_total, tokens_generated_total | Counter |
| 显存 | gpu_memory_used_bytes, kv_cache_blocks_used | Gauge（按 gpu_id 分 labels） |
| 缓存 | kv_cache_hit_rate | Gauge |
| 队列 | queue_length, active_requests | Gauge |
| 事件 | kv_cache_evicted_total, oom_events_total | Counter |

**暴露方式：** `/metrics` 端点，Prometheus 抓取格式

**参考：** `docs/brainstorming/04-api-contracts.md` §3

### 3.5 容错与自愈需求

| 功能 | 规格 |
|------|------|
| 防 OOM | KV Cache LRU 淘汰（>90% 触发）+ 单请求显存预算限制 |
| 防长尾抖动 | Chunked Prefill + prefill_ratio=0.3 限制 |
| 超时保护 | 单请求 30s 强制 kill |
| 健康检查 | `/health` 端点（vLLM 内置） |
| 自动重启 | 交由容器基础设施（Docker/k8s），代码层不做 |

**参考：** `docs/brainstorming/02-kv-cache-lfu.md`（⚠️ 文件名 `lfu` 为历史遗留，内容为 LRU）

### 3.6 交付物需求

| # | 交付物 | 文件 |
|---|--------|------|
| 1 | Docker 镜像 | `Dockerfile` |
| 2 | 启动脚本 | `launch_h100.sh` |
| 3 | 核心优化代码 | `src/kv_cache_manager.py`, `src/scheduler.py` |
| 4 | Prometheus 指标 | `src/metrics_exporter.py` |
| 5 | 调参接口（Mock 预留） | `src/control/tuner_interface.py` |
| 6 | 评测脚本 | `tests/benchmark_*.py` |
| 7 | 实验复现文档 | `docs/REPRODUCTION.md` |
| 8 | 项目说明 | `README.md` |

**一键启动验证：** `bash launch_h100.sh --model deepseek-v4-flash --tensor-parallel-size 8`

---

## 4. 附录

### 4.1 头脑风暴记录与决策追溯

| 决策 | 来源文件 | SRS 章节 | 状态 |
|------|---------|---------|------|
| 自动调优砍掉 → Mock 预留 | `01-scope.md` | §3.1.6 | ✅ |
| KV Cache LRU 淘汰策略 | `02-kv-cache-lfu.md` | §3.1.1 | ✅ |
| Chunked Prefill chunk_size=512 | `03-chunked-prefill-assumption.md` | §3.1.2 | ✅ |
| gRPC 接口 + Mock | `04-api-contracts.md` | §3.1.6 | ✅ |
| 指标假设（待实测校准） | `05-metrics-assumption.md` | §3.2 | ✅ |
| TP=8 + Continuous Batching | `06-tp8-nccl.md` | §3.1.3, §3.1.4 | ✅ |
| 批处理策略（合并至 06） | `07-batching-strategy.md` | §3.1.3 | ✅ |

### 4.2 项目结构

```
deepseek-v4-h100/
├── docs/
│   ├── srs/
│   │   ├── SRS-00-draft.md      ← 当前文件
│   │   ├── figures/            ← 架构图、时序图
│   │   └── SRS-01-final.md     ← 定稿版（头脑风暴结束后）
│   ├── brainstorming/         ← 决策过程记录
│   └── original-requirements.md ← 原始需求归档
├── src/                       ← 代码（头脑风暴后创建）
├── configs/                   ← 配置文件
├── scripts/                   ← 启动脚本
├── tests/                     ← 评测脚本
└── README.md
```
