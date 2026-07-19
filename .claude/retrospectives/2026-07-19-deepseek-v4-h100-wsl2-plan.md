# 复盘记录 2026-07-19

## PLAN_local_dev_wsl2 执行总结

**用户操作:** `/self-improve` — 固化本次深度工作计划的执行经验
**触发场景:** 8 任务计划全部完成（8/8），无报错，可记录经验

---

## 经验 1：threading.Lock 死锁模式

- **问题**: `record_access()` 持有 `self._lock`，调用 `evict_if_needed()` 时再次尝试获取同一个非重入锁 → 死锁
- **原因**: Python `threading.Lock` 不可重入，而 `threading.RLock` 可重入
- **正确做法**: 拆分出 `_evict_locked()` 内部方法，调用方必须已持有锁；公开方法 `evict_if_needed()` 负责获取锁后再调用
- **场景**: 任何在持有锁的情况下调用可能再次获取同一锁的场景
- **来源**: 2026-07-19，KVCacheManager 和 MockKVCacheManager 两次实现

```python
# ✅ 正确模式
def evict_if_needed(self) -> int:
    with self._lock:
        return self._evict_locked()  # 假设调用方已持有锁

def _evict_locked(self) -> int:
    """Caller must hold self._lock."""
    ...

# ❌ 错误模式
def evict_if_needed(self) -> int:
    with self._lock:
        ...  # 在持有锁的情况下做大量 evict 工作
        self._evict_locked()  # 再次获取同一锁 → 死锁
```

---

## 经验 2：vLLM WSL2 CPU 环境关键配置

- **问题**: vLLM 0.25.1+cpu 在 WSL2 上启动崩溃（WorkerProc fork 失败）
- **原因**: vLLM v1 engine 默认开启多进程，fork() 在 WSL2 上有问题；默认 gpu_memory_utilization=0.92 申请内存超限
- **正确做法**: 设置两个环境变量/参数
  - `VLLM_ENABLE_V1_MULTIPROCESSING=0` — 禁用多进程
  - `gpu_memory_utilization=0.5` — 降低内存申请（WSS 上限 15GB）
  - `dtype=bfloat16` — WSL2 CPU 支持 bf16
- **场景**: 在 WSL2 Ubuntu 22.04 无 GPU 环境运行 vLLM CPU mode
- **来源**: 2026-07-19，Task 1 环境搭建

---

## 经验 3：Mock Adapter 测试优先

- **问题**: 直接在 vLLM 上验证核心逻辑（调度、缓存、调优），依赖 8×H100 硬件才能开发
- **原因**: 推理引擎（vLLM）和核心业务逻辑（调度器、LRU 缓存、Agent 调优）强耦合
- **正确做法**: 用 MockAdapter 模拟推理引擎延迟和结果，先在 Mock 上验证完整流程，再切换到真实引擎
- **场景**: 后端推理引擎不可用时（无 GPU、环境受限）开发验证
- **来源**: 2026-07-19，Task 2-4 全部采用 Mock-first 策略

---

## 经验 4：六边形架构端口设计

- **核心原则**: 核心调度逻辑与推理后端完全解耦，通过 Port 接口隔离
- **4 个 Port**: `InferenceEngine`、`SchedulerPort`、`KVCacheManagerPort`、`MetricsCollectorPort`
- **适配器**: `MockAdapter`（开发/测试）+ `VLLMAdapter`（生产）
- **配置驱动切换**: 修改 `configs/model.yaml` 即可切换 WSL2 ↔ H100，无需改动核心代码
- **来源**: 2026-07-19，Task 2 架构实现

---

## 验证清单

- [x] `_evict_locked()` 模式已记录 → 未来遇到锁内调用锁的场景时触发
- [x] vLLM WSL2 配置已记录 → Task 1 经验固化
- [x] Mock-first 策略已记录 → 未来无 GPU 开发时优先使用
- [x] 六边形架构决策已记录 → Task 2 架构经验固化
