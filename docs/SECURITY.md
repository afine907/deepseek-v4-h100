# SECURITY.md — 安全规范

---

## 1. 密钥与凭据

| 禁止 | 正确做法 |
|------|---------|
| 将密钥写入代码 | 使用环境变量或 `.env` 文件（不提交到 git） |
| 将密钥写入配置文件 | 使用 `.env.example` 模板，密钥通过 CI/CD 注入 |
| 提交 `.env` 文件 | 确保 `.gitignore` 包含 `.env` |
| 在日志中打印密钥 | 日志脱敏或直接禁止记录敏感字段 |

### 已知密钥位置（示例，本项目无实际密钥）

- 模型权重 URL（DeepSeek-V4-Flash 权重）— 参赛文档预留位置：`Dockerfile` 中的 `ENV MODEL权重_URL`
- vLLM 内部令牌（未来扩展）

---

## 2. 敏感数据边界

| 数据类型 | 处理方式 |
|----------|----------|
| 用户 prompts | 在 Prometheus metrics 中**不记录** prompt 内容 |
| 生成的代码 | 不持久化到不安全位置 |
| GPU 显存数据 | 仅在内存中计算，不写入磁盘 |
| 错误日志 | 自动过滤 request_id 以外的请求内容 |

---

## 3. 网络安全

- 推理服务端口（8000）**仅监听 localhost**
- 如需远程访问，通过 SSH 隧道或内部代理
- Prometheus metrics endpoint `/metrics` **不鉴权**（仅内网访问）

---

## 4. 容器安全

| 实践 | 说明 |
|------|------|
| 以非 root 用户运行 | Dockerfile 设置 `USER` |
| 最小化 base image | 使用 `nvidia/cuda:12.4.1-runtime-ubuntu22.04`（非 devel） |
| 只读文件系统 | 生产环境考虑 `--read-only` |
| 不运行 SSH daemon | 容器不应有 SSH 服务 |

---

## 5. AI Agent 安全边界

**AI Agent 不得执行以下操作：**

| 禁止操作 | 原因 |
|----------|------|
| 修改 `configs/` 以外的硬编码常量 | 配置必须通过接口修改 |
| 删除 `.dwp/` 目录 | DWP 流程文件由流程管理 |
| 在无监督情况下提交到 `main`/`master` | 所有变更通过 PR |
| 提交含真实密钥的代码 | 即使是"测试"也不行 |
| 修改 Dockerfile 的 `USER` 设置 | 安全边界 |

---

## 6. 错误报告

发现安全问题请通过以下方式报告：

1. **不要**在公开 issue 中描述安全漏洞
2. 联系维护者（优先）或在私有 issue 中标注 `[security]`
