# 头脑风暴记录 #03：Chunked Prefill chunk size 假设

> 日期：2026-07-18
> 状态：⚠️ 待实测校准

---

## 决策结论

**Chunked Prefill chunk size：假设为 512 tokens（可配置参数）**

> ⚠️ 此为假设值，待基线实测后校准

---

## 假设依据

### chunk size 选型的trade-off

```
chunk_size 太小：
  ✅ 长请求被切得更细，短请求等待时间更短
  ❌ 调度开销增大，GPU 利用率下降

chunk_size 太大：
  ✅ 调度开销小，GPU 计算密度高
  ❌ 长请求 prefill 耗时太长，短请求 decode 被阻塞
```

### 假设为 512 的理由

| 因素 | 512 tokens 的优势 |
|------|-----------------|
| GPU 计算效率 | 512 是 2 的幂次，内存对齐友好 |
| 延迟控制 | 512 tokens 的 prefill 在 H100 上约 50-100ms，不会长时间阻塞 |
| 与 vLLM 默认值对齐 | vLLM 内部 Continuous Batching 默认 chunk 大小在同数量级 |
| 上下文窗口适配 | DeepSeek-V4-Flash max_seq_len 充足，512 不是浪费 |

### 待实测后调整

| 场景 | 建议 chunk_size | 备注 |
|------|----------------|------|
| 基线测试 | 512 | 当前假设 |
| 超长上下文（>32k tokens） | 256 或 128 | 进一步切分减少单次阻塞 |
| 短请求为主 | 1024 | 减少调度开销 |

---

## 配置设计

```yaml
# config/chunked_prefill.yaml
chunked_prefill:
  enabled: true
  chunk_size: 512              # tokens per chunk（可覆盖）
  max_chunks_per_request: 64   # 防止超长请求切太多
  prefill_credit_budget: 2     # prefill 每次最多占用的 token budget
```

---

## 反饥饿机制

为防止长请求永远得不到完整 prefill，引入 SJF（Shortest Job First）+ aging 机制：

```
调度优先级分数 = 请求剩余 tokens / (1 + wait_time * aging_factor)

aging_factor = 0.1  # 防止长请求饿死的衰减因子
```

---

## 待确认项

- [ ] DeepSeek-V4-Flash max_seq_len 确认真实值
- [ ] 基线实测 512 是否合适，还是需要调整
- [ ] prefill_credit_budget 的具体数值
