# 文档自闭环验证清单

> 每次文档修改后执行本清单，确保文档集自洽。

---

## 1. 矛盾检查

- [ ] **自动调优状态**：grep "auto_tuner" / "自动调优" 仅在以下位置出现：
  - `01-scope.md`（历史决策记录）
  - `Mock` / `预留` 上下文描述
  - **无其他位置将自动调优描述为活动功能**
- [ ] **SRS 章节编号**：无重复，所有 `3.1.x` 编号唯一且连续
- [ ] **批处理术语**：所有文档使用一致描述（"迭代级批处理"/"等待结束再插入"）
- [ ] **07 文件状态**：明确标注为"纯历史参考"

## 2. 交叉引用检查

- [ ] **图引用完整**：README 架构图表包含图 1-7（不是只有 1-5）
- [ ] **competition-document** 各优化小节均有 SRS 对应章节引用
- [ ] **架构图来源注释**：图 6（图 6 数据来源）、图 7（图 7 代码路径来源）已标注
- [ ] **SRS 决策追溯矩阵**：`§4.1` 附录已从纯文件列表替换为决策追溯矩阵
- [ ] **LFU/LRU 注释**：3 处文件名历史遗留注释均已添加

## 3. 文档版本/状态检查

- [ ] **SRS**：`状态：草案 · 待最终确定`
- [ ] **competition-document**：`状态：初始版`
- [ ] **版本号**：无文件声称 `v0.1` 同时又是 `v1.0`

## 4. 悬空引用检查

- [ ] **占位符文件存在**：`configs/`、`src/README.md`、`tests/README.md`、`Dockerfile`、`launch_h100.sh`、`requirements-dev.txt`、`docs/REPRODUCTION.md`
- [ ] **配置文件路径统一**：`configs/`（复数），无 `config/`（单数）
- [ ] **README 项目结构**：所有占位符文件标注 `# ⏳ 待创建`
- [ ] **无引用不存在的 `.py` 文件**
- [ ] **无引用不存在的 `docs/REPRODUCTION.md`**

## 5. 决策链追溯检查

每个 brainstorming 决策都在 SRS 中有对应章节：

| 决策 | SRS 章节 |
|------|---------|
| 自动调优砍掉 → Mock | §3.1.6 |
| KV Cache LRU | §3.1.1 |
| Chunked Prefill chunk_size=512 | §3.1.2 |
| gRPC 接口 + Mock | §3.1.6 |
| 指标假设 | §3.2 |
| TP=8 + Continuous Batching | §3.1.3, §3.1.4 |

## 6. 指标表一致性检查

以下 5 个核心指标在所有文档中值一致：

| 指标 | 值 |
|------|---|
| P99 延迟基线 | 10.0 s |
| QPS 基线 | 50 |
| GPU 利用率目标 | > 80% |
| KV Cache 命中率目标 | > 70% |
| SWE-bench 完成率目标 | > 99% |

**检查方法**：`grep` 各文档中的上述 5 个数字是否匹配。

---

## 快速验证命令

```bash
# 1. 检查 auto_tuner 是否仍有活动引用
grep -r "auto_tuner" docs/ --include="*.md" | grep -v "01-scope\|Mock\|tuner_interface"
# 期望：无输出

# 2. 检查 SRS 章节编号是否唯一
grep "3\.1\.[1-9]" docs/srs/SRS-00-draft.md | grep "^#" | sort | uniq -d
# 期望：无输出

# 3. 检查配置文件路径（无单数 config/）
grep -r "config/chunked_prefill" docs/ --include="*.md"
# 期望：无输出（已统一为 configs/）

# 4. 检查 README 是否包含图 6 和图 7
grep "图-6\|图-7\|图 6\|图 7" README.md
# 期望：有输出

# 5. 检查占位符文件
ls configs/*.yaml src/README.md tests/README.md Dockerfile launch_h100.sh requirements-dev.txt docs/REPRODUCTION.md 2>&1
# 期望：全部存在
```

---

## 最近修改记录

| 日期 | 修改内容 | 验证者 |
|------|---------|--------|
| 2026-07-18 | Phase 1-4 全部文档自闭环修复 | |
