# AI_AGENT_COLLAB.md — 协作规范

> 本文件定义多个 AI Agent（或 Agent 与人类）协作时的规则。

---

## 1. 任务交接

当一个 Agent 需要将任务移交给另一个 Agent 时：

1. **记录上下文**：在 PR description 或任务注释中写入：
   - 已完成的工作
   - 关键决策和原因
   - 未解决的问题和风险
   - 下一步行动

2. **文件状态**：
   - 交接前确认所有文件已保存
   - 交接时提供关键文件路径列表

3. **不要假设**：接收方 Agent 不知道交接前的对话上下文，必须提供完整信息。

---

## 2. 冲突避免

| 场景 | 规则 |
|------|------|
| 同一模块被多个 Agent 并行修改 | 使用 git branch 隔离，每人一个分支 |
| PR review 意见冲突 | 在 PR thread 中讨论，以 AGENTS.md 规范为准 |
| 配置文件与代码不一致 | 以代码为准，配置文件作为辅助；如需改配置，同时更新代码 |
| DWP 计划与实际不符 | 更新 `.dwp/plans/PLAN_xxx/PROGRESS.md`，不要忽略不一致 |

---

## 3. 进度同步

- **每个 PR** 必须包含 progress report（在 description 或 commit message）
- **阻塞问题** 必须立即标注（`@afine907`、`[blocked]`）
- **DWP 任务** 完成后更新 `PROGRESS.md`

---

## 4. 任务优先级

```
P0: 让测试通过（Mock 测试优先）
P1: 实现核心调度逻辑（scheduler.py）
P2: 实现 KV Cache 管理（kv_cache_manager.py）
P3: 实现 metrics（metrics_exporter.py）
P4: 实现 vLLM 封装（inference_engine.py）
P5: 调参和性能优化
```

---

## 5. Deep Work Plan 协作

当使用 DWP（DeepWorkPlan）流程时：

- **Plan 创建**：在 `.dwp/drafts/` 生成草稿，由人类确认
- **执行记录**：每个任务完成后，写入 `PROGRESS.md` 的 task summary
- **审查点**：重大决策（架构变更、PR scope 扩大）提交 human review
- **不阻塞**：Agent 在不确定时，先做最有把握的部分，标记 `[uncertain]` 继续

---

## 6. 错误恢复

| 错误类型 | 处理方式 |
|----------|----------|
| 测试变红 | 立即停止当前工作，修复测试 |
| Merge conflict | 联系冲突方协商，不自动接受任一方 |
| DWP 计划过时 | 更新计划，不忽略；向 human 确认是否调整目标 |
| vLLM API 不兼容 | 在 PR 中标注，在 `docs/brainstorming/` 创建决策记录 |

---

## 7. 沟通格式

PR / commit message / DWP 任务报告统一格式：

```
## What
<简短描述做了什么>

## Why
<为什么这样做的原因>

## Outstanding
<未解决的问题和风险>
```
