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

### vLLM WSL2 CPU 性能优化（实测有效）
- **问题**: 首次启动 647 秒，libiomp 警告，输出 11.35 toks/s
- **两根优化**:（1）`TORCH_COMPILE_DISABLE=1` 禁用 JIT 编译；（2）`LD_PRELOAD` 加载优化库
- **正确做法**:
  - `TORCH_COMPILE_DISABLE=1` — 禁用 torch.compile 强制 eager mode，启动快 24%（647s→494s）
  - `LD_PRELOAD=/root/deepseek-local/venv/lib/libiomp5.so:/usr/lib/x86_64-linux-gnu/libtcmalloc_minimal.so.4`
    - libiomp5.so 在 vLLM venv 中；tcmalloc 系统已安装
    - 消除 `libiomp is not found in LD_PRELOAD` 警告
    - 输出速度从 10.34 恢复到 11.36 toks/s
- **持久化**: 将 LD_PRELOAD 写入 `~/.bashrc`
- **场景**: WSL2 CPU 推理优化（不适用 H100，H100 有 GPU）
- **来源**: 2026-07-19，实测对比

---

### vLLM WSL2 排查要先查文档不要盲目尝试
- **错误**: 遇到 vLLM WSL2 问题直接本地尝试各种修复，浪费数小时
- **原因**: vLLM 在 WSL2 上有多个已知问题（fork/OOM/配置），社区有现成方案
- **正确做法**: 遇到环境兼容性问题，先用 anysearch 搜索已知 Bug 和最佳实践，确认方向后再动手
- **场景**: vLLM / WSL2 / Docker 等环境问题排查
- **来源**: 2026-07-19，用户复盘
