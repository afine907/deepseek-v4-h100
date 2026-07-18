# 头脑风暴记录 #07：动态批处理策略

> 日期：2026-07-18
> 状态：✅ 已决策（合并至 06-tp8-nccl.md，以 06 为准）

---

> ⚠️ 本文件内容已合并至 `06-tp8-nccl.md`，保留此文件作为历史记录。

## 决策总结

| 项目 | 决策 |
|------|------|
| 批处理模式 | Continuous Batching |
| 插入策略 | 等待 batch 结束再插入（不使用 Micro-Batching） |
| prefill_ratio | 0.3 |
| max_batch_size | 32 |
| max_wait_time_ms | 100 |

---

## 为什么不使用 Micro-Batching

TP=8 + MoE All-to-All 场景下：
- Micro-Batching 的切换 overhead 大于其带来的吞吐提升
- MoE 长请求为主，等待 batch 结束的利用率损失可接受
- 实现简单，2周内可稳定交付

---

## 参考

- `06-tp8-nccl.md` — 包含完整分析
