# PRODUCT_SPEC.md — 产品规格

> 本文件描述 DeepSeek-V4-Flash 8×H100 推理优化系统的**非技术层面**定位：
> 这个系统是什么、为谁服务、解决什么问题、成功是什么样。

---

## 1. 问题背景

AI Coding 场景（如 SWE-bench 代码修复任务）对大模型推理服务提出了极端挑战：

- **长上下文**：代码仓库级依赖，单请求 token 数可达数万
- **长尾延迟**：突发长请求导致 P99 延迟剧烈抖动
- **GPU 利用率不足**：Prefill/Decode 阶段互相等待，资源空转
- **显存压力**：KV Cache 随并发线性增长，OOM 风险高

这些问题在 8×H100 NVLink 集群上更为突出——算力充足，但调度不当导致效率远低于硬件上限。

---

## 2. 目标用户

| 用户 | 场景 |
|------|------|
| **SWE-bench 评测系统** | 批量运行代码修复任务，收集 P99/QPS 指标 |
| **AI Coding 应用** | 需要高吞吐、低延迟代码补全的服务（future） |
| **MLOps 团队** | 调优推理服务参数、观察 Prometheus 指标 |

---

## 3. 核心能力

| 能力 | 说明 | 状态 |
|------|------|------|
| Chunked Prefill | 将长输入切分为 512 tokens 块，消除长请求对 Decode 的阻塞 | ⏳ 待实现 |
| Continuous Batching | 迭代级动态批处理，最大批 32 请求 | ⏳ 待实现 |
| KV Cache LRU 淘汰 | 显存超过 90% 时自动淘汰最少使用块，防止 OOM | ⏳ 待实现 |
| TP=8 分布式推理 | 8×H100 NVLink 全互联，NCCL 优化 | ⏳ 待实现 |
| Prometheus 可观测 | 延迟分布、GPU 显存、KV Cache 命中率等指标 | ⏳ 待实现 |
| FP8 量化 | 精度/显存平衡 | ⏳ 待实现 |

---

## 4. 成功标准

| 指标 | 基线（假设） | 目标 |
|------|------------|------|
| P99 延迟 | 10.0 s | < 5.0 s |
| QPS | 50 | > 100 |
| GPU 利用率 | 50% | > 80% |
| KV Cache 命中率 | 40% | > 70% |
| SWE-bench 完成率 | 95% | > 99% |

> ⚠️ 基线为假设值，待实测后校准。见 [docs/brainstorming/05-metrics-assumption.md](brainstorming/05-metrics-assumption.md)

---

## 5. 非目标（明确不做）

- Streaming 输出（参赛重点是吞吐和延迟，非首 token 速度）
- 实时在线调参闭环（4 小时赛程内不做，控制层为 Mock/预留）
- Multi-GPU 弹性扩缩容（固定 8×H100）
- 非 DeepSeek-V4-Flash 模型支持

---

## 6. 系统边界

| 在系统内 | 在系统外 |
|----------|----------|
| 请求调度（Chunked Prefill + Continuous Batching） | 模型权重下载和管理 |
| KV Cache 块管理（LRU 淘汰） | 网络传输层 |
| vLLM 引擎封装 | 代码仓库解析 |
| Prometheus 指标导出 | SWE-bench 评测流程（调用本系统） |
| Docker 容器启动 | 外部负载均衡器 |

---

## 7. 关键约束

- **硬件**：8× NVIDIA H100 (80GB)，NVLink 全互联
- **CUDA**：12.x
- **Python**：3.10+
- **推理引擎**：vLLM（直接调用，不自研）
- **容器化**：Docker，nvidia/cuda:12.4.1-runtime-ubuntu22.04
