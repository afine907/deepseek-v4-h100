# 通用经验规则

> 自动积累的项目经验，Claude 每次会话会自动读取

### Python threading.Lock 死锁模式
- **错误**: 在持有 `threading.Lock` 的方法内部调用另一个也要获取同一把锁的方法 → 死锁
- **原因**: `threading.Lock` 不可重入；`threading.RLock` 才可重入
- **正确做法**: 拆分出 `_xxx_locked()` 内部方法（假设调用方已持有锁）+ 公开方法（获取锁后调用内部方法）
- **场景**: 任何在持有锁的情况下调用可能再次获取同一锁的场景
- **来源**: 2026-07-19，KVCacheManager 两次实现

---

### Mock Adapter 优先验证
- **错误**: 直接在真实引擎（vLLM/H100）上验证核心逻辑，依赖硬件才能开发
- **原因**: 核心逻辑（调度/缓存/调优）与推理引擎强耦合
- **正确做法**: 先用 MockAdapter 模拟引擎延迟和结果验证完整流程，再切换真实引擎
- **场景**: 无 GPU 或环境受限时开发验证；CI 测试
- **来源**: 2026-07-19，Task 2-4 全部采用 Mock-first 策略

---

### 测试断言前先诊断实际行为
- **错误**: 写测试时用"猜测"代替"观测"，断言基于错误假设（如 `evict >= 0` 永远真、`usage == 0.3` 期望值）导致大量失败
- **原因**: 不理解被测系统实际行为（触发时机、数据流向、边界条件），凭印象写断言
- **正确做法**: 写断言前，用 `python -c "..."` 单独诊断目标模块/类的实际行为，再用真实行为写断言
- **场景**: 写任何非-trival 测试时（尤其是边界条件、时序相关、并发相关）
- **来源**: 2026-07-19，重写 21 个失败测试时反复试错

---

### Python 数据结构方法返回值
- **错误**: 假设 `dict.popitem()` / `OrderedDict.popitem(last=False)` 返回值直接可用，或误判返回值类型
- **原因**: `popitem()` 在 Python 3.7+ 是有顺序的，但不同数据结构方法签名不同
- **正确做法**: 写测试前用 `python -c "import X; help(X.method)"` 确认签名；用实际调用验证返回值
- **场景**: 测试涉及数据结构操作时
- **来源**: 2026-07-19，KVCacheManager `_evict_locked` 调试

---

### Mock 与真实实现行为差异
- **错误**: 假设 Mock 和真实实现行为完全一致，用 Mock 的行为断言套用到真实类上
- **原因**: MockKVCacheManager 和 KVCacheManager eviction 触发时机不同（mock auto-evict 在 miss 路径实现不同）
- **正确做法**: 两者都单独诊断实际行为后再写测试；如果行为不同，测试应分别验证各自的行为
- **场景**: 同时测试 Mock 和真实实现时
- **来源**: 2026-07-19，KVCacheManager vs MockKVCacheManager eviction 测试

---

### Claude Code rules 文件格式
- **错误**: 使用 `globs` 字段做文件 scoped 规则（Cursor 格式）
- **原因**: Claude Code 使用 `paths` + YAML 列表格式，不支持 `globs`
- **正确做法**: 使用 `paths:` + YAML 列表格式，例如：
  ```yaml
  paths:
    - "**/*.ts"
    - "**/*.test.ts"
  ```
  全局规则无 frontmatter
- **场景**: 编写 `.claude/rules/*.md` 文件时
- **来源**: 2026-07-19，rules 格式纠正
