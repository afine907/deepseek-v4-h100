# AGENTS.md

> DeepSeek-V4-Flash 8×H100 推理优化系统 — AI Agent 工作索引

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | 产品规格：问题定义、目标用户、核心能力 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构：四层结构、模块边界、数据流 |
| [docs/STANDARDS.md](docs/STANDARDS.md) | 编码规范：命名、导入、日志、禁止事项 |
| [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | 测试指南：框架、命令、覆盖率目标 |
| [docs/DEVELOPMENT_COMMANDS.md](docs/DEVELOPMENT_COMMANDS.md) | 开发命令：安装、构建、测试、运行 |
| [docs/SECURITY.md](docs/SECURITY.md) | 安全规范：密钥、环境变量、敏感数据 |
| [docs/AI_AGENT_ONBOARDING.md](docs/AI_AGENT_ONBOARDING.md) | AI Agent 首次上手 Checklist |
| [docs/AI_AGENT_COLLAB.md](docs/AI_AGENT_COLLAB.md) | 协作规范：任务交接、冲突处理、进度同步 |
| [docs/VALIDATION.md](docs/VALIDATION.md) | 验证方案：SWE-bench 评测流程 |
| [docs/brainstorming/](docs/brainstorming/) | 决策记录（历史） |
| [docs/srs/](docs/srs/) | 系统需求规格 |

### 源代码模块文档

| 模块 | 说明 |
|------|------|
| [src/scheduler.md](src/scheduler.md) | Chunked Prefill + Continuous Batching 调度器 |
| [src/kv_cache_manager.md](src/kv_cache_manager.md) | KV Cache LRU 淘汰管理器 |
| [src/inference_engine.md](src/inference_engine.md) | vLLM 引擎封装 |
| [src/metrics_exporter.md](src/metrics_exporter.md) | Prometheus 指标导出器 |
| [src/control/tuner_interface.md](src/control/tuner_interface.md) | 调参接口（Mock） |

---

## 项目结构

```
deepseek-v4-h100/
├── AGENTS.md                          # 本文件
├── CLAUDE.md                          # → AGENTS.md (symlink)
├── Dockerfile                         # 容器镜像
├── launch_h100.sh                     # 启动脚本
├── requirements-dev.txt               # 开发依赖
├── configs/                          # 配置文件
│   ├── model.yaml                    # 模型配置
│   ├── batching.yaml                 # 批处理配置
│   ├── scheduler.yaml                # 调度配置
│   └── kv_cache.yaml                 # KV Cache 配置
├── src/                              # 源代码
│   ├── scheduler.py                  # 调度层
│   ├── kv_cache_manager.py           # KV Cache 管理
│   ├── inference_engine.py           # vLLM 封装
│   ├── metrics_exporter.py           # Prometheus metrics
│   ├── control/
│   │   └── tuner_interface.py        # 调参接口（Mock）
│   └── *.md                          # 模块文档
├── tests/                            # 测试
│   ├── unit/                         # 单元测试
│   ├── integration/                  # 集成测试
│   ├── benchmark_swe.py              # SWE-bench 评测
│   └── conftest.py                   # pytest 配置
├── docs/                             # 文档
│   ├── PRODUCT_SPEC.md               # 产品规格
│   ├── ARCHITECTURE.md               # 系统架构
│   ├── STANDARDS.md                  # 编码规范
│   ├── TESTING_GUIDE.md             # 测试指南
│   ├── DEVELOPMENT_COMMANDS.md       # 开发命令
│   ├── SECURITY.md                   # 安全规范
│   ├── AI_AGENT_ONBOARDING.md        # AI Agent 上手
│   ├── AI_AGENT_COLLAB.md           # 协作规范
│   ├── VALIDATION.md                 # 验证方案
│   ├── brainstorming/                # 头脑风暴（决策记录）
│   └── srs/                         # 需求规格
└── .dwp/                            # Deep Work Plan 输出（gitignored）
    ├── plans/                        # 已确认的执行计划
    └── drafts/                       # 计划草稿
```

---

## 强制规则

### 提交规范（Conventional Commits）

所有 commit message 必须使用以下格式：

```
type(scope): description

type:    feat | fix | docs | style | refactor | test | chore | perf
scope:   源码模块名，如 scheduler / kv_cache_manager / inference_engine
         或通用：core | config | docker | ci
```

示例：
```
feat(scheduler): 实现 Chunked Prefill 分块逻辑
fix(kv_cache_manager): 修复 LRU 淘汰时块引用计数错误
docs(TESTING_GUIDE): 更新 SWE-bench 评测命令
chore(docker): 升级 nvidia/cuda 到 12.4.1
```

**不得提交：无意义的 commit（如 "update"、"fix typo"）、破坏性变更未经讨论、placeholder 代码未经标注。**

### 测试规则

- 所有新增功能 **必须** 伴随单元测试或 Mock 测试
- 测试文件命名：`*_test.py`（单元），`*_mock_test.py`（Mock），`*_integration_test.py`（集成）
- Mock 测试命令：`pytest tests/ -m mock`（无 GPU 环境下运行）
- 单元测试命令：`pytest tests/unit/ -v`
- 测试覆盖率目标：核心模块（scheduler、kv_cache_manager）≥ 80%
- **禁止** 提交让整体测试套件变红的代码

### 日志与错误规范

- 使用 `logging` 模块，**不得** 使用 `print` 调试
- 日志级别：`DEBUG`（开发细节）、`INFO`（正常流程）、`WARNING`（可恢复异常）、`ERROR`（需关注的错误）
- 所有异常必须带上下文信息（request_id、模块名、关键参数）
- Prometheus metrics 暴露使用 `prometheus_client` 库

### 范围边界

| 可以做 | 不得做 |
|--------|--------|
| 修改 `src/` 下各模块实现 | 直接提交到 `main` / `master` 分支 |
| 添加 `tests/` 测试 | 在不了解现有架构的情况下做全局重构 |
| 修改 `configs/` 配置文件 | 删除或绕过已有的测试 guard |
| 更新 `docs/` 文档 | 改动 `.dwp/` 内文件（由 DWP 流程管理） |
| 创建新 branch 并提 PR | 在没有验证的情况下关闭 feature flag |

### 进度汇报

- 每个任务完成后，在 PR description 或任务注释中记录：
  - 做了什么
  - 关键决策和原因
  - 无法确定的悬空问题
- **不因汇报而阻塞工作** — 先干，后同步
- 如遇阻塞（设计决策、依赖缺失），立即在 PR 或任务注释中标注 `@afine907`

---

## Quick Commands

| 操作 | 命令 | 适用范围 |
|------|------|---------|
| 安装开发依赖 | `pip install -r requirements-dev.txt` | 本地 |
| 运行 Mock 测试 | `pytest tests/ -m mock` | 本地（无 GPU） |
| 运行单元测试 | `pytest tests/unit/ -v` | 本地（无 GPU） |
| 构建 Docker 镜像 | `docker build -t deepseek-v4-h100 .` | **需 GPU** |
| 启动推理服务 | `bash launch_h100.sh --model deepseek-v4-flash --tensor-parallel-size 8` | **需 8×H100** |
| 查看启动帮助 | `bash launch_h100.sh --help` | 本地 |
| SWE-bench 评测 | `python tests/benchmark_swe.py --output results.json` | **需 GPU** |
| 查看 metrics | `curl http://localhost:8000/metrics` | 服务运行中 |

> **标注 "需 GPU" 的命令**必须在具备 8× NVIDIA H100 的环境中运行，不能在普通开发机上执行。
