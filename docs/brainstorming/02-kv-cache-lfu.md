# 头脑风暴记录 #02：KV Cache 淘汰策略决策

> 日期：2026-07-18
> 状态：✅ 已决策（2026-07-18 更新：LFU → LRU）
>
> ⚠️ **文件名历史说明**：文件名中的 `lfu` 是历史命名遗留——本文件记录的决策为 **LRU**（Least Recently Used），非 LFU。

---

## 决策结论

**KV Cache 淘汰策略：LRU（Least Recently Used）**

| 策略 | 选择 | 理由 |
|------|------|------|
| LRU | ✅ | 简单高效，实现复杂度低，适合长尾分布的 SWE-bench 请求模式 |
| LFU | ❌ | 频率统计有额外开销，且新请求的缓存竞争劣势明显 |
| 混合 | ❌ | 实现复杂度高，2周时间优先保证核心功能 |

---

## LRU 淘汰机制设计

### 淘汰触发条件

```
触发条件（满足任一）：
1. 显存使用率 > GPU_MEMORY_HIGH_WATERMARK（默认 90%）
2. 可用 KV Cache block 数 < MIN_FREE_BLOCKS（默认 10）
```

### 淘汰执行逻辑

```
1. 遍历所有活跃 request 的 KV Cache block
2. 按 last_access_time（最后访问时间）升序排序（最老的排前面）
3. 从最久未访问的 block 开始淘汰
4. 淘汰直到满足停止条件：
   - 显存使用率 < GPU_MEMORY_LOW_WATERMARK（默认 75%）
   - 或已淘汰 MAX_EVICT_PER_ROUND 个 block（默认 50）
```

### 访问时间更新机制

```
每次请求对 KV Cache block 产生新 token 时，更新 last_access_time
在连续 decode 阶段，同一请求的 block 可能短时间内多次访问
这正好符合 LRU 的局部性原理：最近访问的更可能再次访问
```

---

## 待确认项

- [ ] 高水位/低水位阈值是否需要可配置
- [ ] MAX_EVICT_PER_ROUND 的数值是否合理
