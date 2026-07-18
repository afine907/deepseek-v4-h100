# kv_cache_manager.py — KV Cache LRU 淘汰管理器

> ⏳ 本模块为占位符，待实现。

---

## 模块职责

`kv_cache_manager.py` 负责管理 vLLM 的 KV Cache 块生命周期：

1. **显存监控** — 监控 GPU 显存使用量
2. **块分配** — 为新请求分配 KV Cache blocks
3. **LRU 淘汰** — 当显存超过 high_watermark 时，淘汰最少使用的 blocks
4. **水位控制** — 淘汰直到显存降至 low_watermark

---

## 公开接口

```python
class KVCacheManager:
    def allocate(self, request_id: str, num_blocks: int) -> List[int]:
        """为请求分配 num_blocks 个 KV Cache 块。

        Returns:
            分配的 block ID 列表。

        Raises:
            KVCacheError: 显存不足且无法淘汰。
        """

    def release(self, request_id: str) -> None:
        """释放请求持有的所有 KV Cache 块。"""

    def evict(self) -> int:
        """执行 LRU 淘汰，返回淘汰的块数。"""

    def get_status(self) -> KVCacheStatus:
        """获取当前 KV Cache 状态。"""
```

### 数据结构

```python
@dataclass
class KVCacheStatus:
    used_blocks: int
    available_blocks: int
    hit_rate: float  # 命中率（0.0~1.0）
    total_evicted: int  # 历史累计淘汰块数
    oom_events: int  # OOM 事件次数
```

---

## LRU 淘汰算法

```
evict() 触发条件：gpu_memory_usage > high_watermark (0.90)

步骤：
1. 按 last_access_time 升序排序所有已分配的 blocks
2. 弹出最少使用的 block
3. 标记为 evicted（通知 vLLM）
4. 重新检查：if gpu_memory_usage > low_watermark (0.75) → 回到步骤 1
5. 返回淘汰的 block 数
```

**关键参数**：
- `high_watermark: 0.90` — 触发淘汰的显存水位
- `low_watermark: 0.75` — 停止淘汰的显存水位

---

## 与 vLLM 的交互

vLLM 的 `BlockManager` 负责实际的 block 分配/释放。
`kv_cache_manager.py` 封装对 `BlockManager` 的调用，并添加 LRU 淘汰策略。

```python
# 预期的 vLLM 交互（待确认）
from vllm.block_manager import BlockManager

self.block_manager = BlockManager(...)
self.block_manager.allocate(request_id, num_blocks)
self.block_manager.free(block_id)
```

---

## 依赖关系

```
kv_cache_manager.py
└── inference_engine.py（获取 vLLM block_manager 实例）
```

---

## 配置参数（来源：configs/kv_cache.yaml）

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `淘汰策略` | LRU | 淘汰算法 |
| `high_watermark` | 0.90 | 触发淘汰的显存水位 |
| `low_watermark` | 0.75 | 停止淘汰的显存水位 |

---

## Metrics（由 metrics_exporter.py 暴露）

| 指标 | 类型 | 说明 |
|------|------|------|
| `kv_cache_blocks_evicted_total` | Counter | 累计淘汰块数 |
| `kv_cache_hit_rate` | Gauge | 命中率 |
| `oom_events_total` | Counter | OOM 事件次数 |
| `gpu_memory_used_bytes` | Gauge | GPU 显存占用 |

---

## 测试

```bash
pytest tests/unit/test_kv_cache_manager.py -v
pytest tests/ -m mock -v  # 使用 MockInferenceEngine
```

---

## 状态

⏳ **待实现** — 接口定义见 [docs/brainstorming/04-api-contracts.md](../docs/brainstorming/04-api-contracts.md)
