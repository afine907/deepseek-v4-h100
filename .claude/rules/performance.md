# 性能与运行环境规则

> vLLM / WSL2 / 推理引擎相关的关键配置经验

### vLLM WSL2 CPU 环境关键配置
- **错误**: vLLM 0.25.1+cpu 在 WSL2 上启动崩溃（WorkerProc fork 失败）或 OOM
- **原因**: vLLM v1 engine 默认多进程 fork() 在 WSL2 有问题；默认 gpu_memory_utilization=0.92 申请内存超 15GB 上限
- **正确做法**: 必须同时设置以下参数/环境变量：
  1. `VLLM_ENABLE_V1_MULTIPROCESSING=0` — 禁用多进程
  2. `gpu_memory_utilization=0.5` — 降低内存申请（WSL2 上限 ~15GB）
  3. `dtype=bfloat16` — WSL2 CPU 支持 bf16
  4. 模型路径使用绝对路径（不用 `~` 展开）
- **场景**: 在 WSL2 Ubuntu 22.04 无 GPU 环境运行 vLLM CPU mode
- **来源**: 2026-07-19，Task 1 环境搭建

---

### vLLM WSL2 排查要先查文档不要盲目尝试
- **错误**: 遇到 vLLM WSL2 问题直接本地尝试各种修复，浪费数小时
- **原因**: vLLM 在 WSL2 上有多个已知问题（fork/OOM/配置），社区有现成方案
- **正确做法**: 遇到环境兼容性问题，先用 anysearch 搜索已知 Bug 和最佳实践，确认方向后再动手
- **场景**: vLLM / WSL2 / Docker 等环境问题排查
- **来源**: 2026-07-19，用户复盘
