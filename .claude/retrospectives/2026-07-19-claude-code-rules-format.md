# 复盘记录 2026-07-19

## 1. 事件回顾
- **用户说了什么**: "你写的 rule 格式不对，Claude Code 用的是 paths 不是 globs，而且 globs 在 Claude Code 里根本不提供文件 scoping。"
- **AI 做错了什么**: 在 `.claude/rules/*.md` 文件中使用了 `globs` 字段做文件 scoped 规则，并使用了 YAML 列表格式
- **正确做法应该是什么**: Claude Code rules 文件应使用 `paths: "pattern"`（单个字符串）做文件 scoped，全局规则无 frontmatter

## 2. 根因分析
- **直接原因**: AI 混淆了 Cursor 编辑器和 Claude Code 的规则格式，将 `globs` 误认为是 Claude Code 支持的字段
- **根本原因**: CLAUDE.md / rules 缺少 Claude Code 规则格式规范；self-improve skill 的 reference 文件虽有正确格式说明，但 AI 未遵循

## 3. 修复措施
- **修改了哪个文件**: `D:\Code\deepseek-v4-h100\.claude\rules\general.md`
- **新增/修改了什么内容**: 新增了一条关于 Claude Code rules 文件格式的教训
- **内容预览**:

  ```markdown
  ### Claude Code rules 文件格式
  - **错误**: 使用 `globs` 字段做文件 scoped 规则，YAML 列表格式写 `paths`
  - **原因**: `globs` 是 Cursor 编辑器的格式；Claude Code 用 `paths` 且只支持单个模式，YAML 列表格式完全不工作
  - **正确做法**: Claude Code 规则 frontmatter 中使用 `paths: "pattern"`（单个字符串），全局规则无 frontmatter
  - **场景**: 编写 `.claude/rules/*.md` 文件时
  - **来源**: 2026-07-19，rules 格式纠正
  ```

## 4. 验证
- [x] 未来遇到类似场景时，这条规则会被触发
- [x] 写入内容简洁可操作（< 5 行）
