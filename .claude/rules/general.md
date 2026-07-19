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
