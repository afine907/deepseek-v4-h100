# 头脑风暴记录 #06：TP=8 通信瓶颈分析

> 日期：2026-07-18
> 状态：✅ 已决策

---

## 决策结论

**并行策略：TP=8 + 等待结束再插入**

| 项目 | 决策 | 理由 |
|------|------|------|
| TP/DP 切分 | **TP=8**（张量并行 8 卡） | 题目要求；MoE 模型单次推理需全部 expert，切分引额外复杂度 |
| 跨卡通信 | **NCCL 调参**（不做自定义 routing） | 2周内自定义 routing 风险太高 |
| 批处理模式 | **Continuous Batching + 等待结束再插入** | TP=8 下 Micro-Batching 的切换 overhead 反而是瓶颈 |

---

## TP=8 通信分析

### MoE All-to-All 特性

```
Dense 模型：每层 AllReduce（所有 GPU 同步）→ O(层数 × 参数量/8)
MoE 模型：每层 All-to-All（token routing 到不同 expert）→ 通信量更大
```

8×H100 NVLink 互联（节点内）：
- NVLink 双向带宽：900 GB/s
- 理论可支撑大规模 All-to-All

### NCCL 环境变量配置

```bash
# 写入容器启动脚本或 Dockerfile ENV
ENV NCCL_MIN_NCHANNELS=8
ENV NCCL_MAX_NCHANNELS=16
ENV NCCL_IB_TIMEOUT=20
ENV NCCL_IB_RETRY_CNT=7
# 生产环境注释掉 DEBUG 相关行
ENV NCCL_DEBUG=INFO
ENV NCCL_DEBUG_FILE=/tmp/nccl_log
```

### 负载均衡注意事项

```
风险：MoE routing 不一定均匀，某些 expert 在某些 GPU 过热
监控：在 Prometheus 中增加 per-GPU expert 负载指标
缓解：vLLM MoE 支持 expert 负载均衡配置（需确认是否默认开启）
```

---

## 批处理策略

### Continuous Batching（等待结束再插入）

> **释义：** "等待结束再插入" 指在**解码迭代边界**检查新请求并插入，而非强制等到整个 batch 完全空闲（后者才是纯 Continuous Batching 的区别点）。在 TP=8 + MoE 场景下，迭代边界插入比完全空闲时才插入能更好地平衡 All-to-All 切换开销。

```
时间 →
┌──────────────────────────────────────────────────────────┐
│ Batch 1: [ReqA][ReqB][ReqC][ReqD]                       │
│              │ 迭代边界 → 检查新请求                          │
│              ReqE 插入 → [ReqA][ReqB][ReqC][ReqD][ReqE]   │
│              │ 迭代边界 → 检查新请求                          │
│              ReqF 插入 → [ReqB][ReqC][ReqD][ReqE][ReqF]   │
└──────────────────────────────────────────────────────────┘

对比 Micro-Batching：
  - Micro-Batching 在 TP=8 + MoE All-to-All 下，切换 overhead 大
  - 等待结束再插入实现简单，在长请求为主的场景下利用率损失可接受
```

### 关键参数配置

```yaml
# configs/batching.yaml
batching:
  max_batch_size: 32           # 8×H100 显存决定
  max_tokens_per_batch: 8192

  # 调度策略
  prefill_ratio: 0.3           # 保守设置，防长请求霸占 GPU
  min_decode_slots: 8         # 保留 decode 槽位，防止饿死
  max_wait_time_ms: 100       # 凑批超时，超过就强制执行
  aging_factor: 0.1           # 长请求优先级提升（防止饿死）

  # 不使用 Micro-Batching
  micro_batch_enabled: false
```

---

## 待确认项

- [ ] vLLM MoE 的 expert 负载均衡是否默认开启
- [ ] max_batch_size=32 是否在 8×H100 显存限制内（需要实测）
- [ ] prefill_ratio=0.3 是否需要根据 SWE-bench 实际请求分布调整
