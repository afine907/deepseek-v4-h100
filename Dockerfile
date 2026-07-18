# DeepSeek-V4-Flash 8×H100 推理容器镜像
# 参考: docs/original-requirements.md, docs/competition-document.md

FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# 安装基础依赖
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip git curl \
    && rm -rf /var/lib/apt/lists/*

# 安装 PyTorch
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 安装 vLLM（含 DeepSeek-V4-Flash 支持）
# TODO: 确认 vLLM 版本与 DeepSeek-V4-Flash 的兼容性
RUN pip install vllm>=0.6.0

# 安装 Prometheus 客户端
RUN pip install prometheus-client

# NCCL 环境变量（参考 docs/brainstorming/06-tp8-nccl.md）
ENV NCCL_MIN_NCHANNELS=8
ENV NCCL_MAX_NCHANNELS=16
ENV NCCL_IB_TIMEOUT=20
ENV NCCL_IB_RETRY_CNT=7
# ENV NCCL_DEBUG=INFO
# ENV NCCL_DEBUG_FILE=/tmp/nccl_log

# 工作目录
WORKDIR /app

# 复制配置文件
COPY configs/ /app/configs/

# 入口脚本（TODO: 替换为真实启动逻辑）
COPY launch_h100.sh /app/launch_h100.sh
RUN chmod +x /app/launch_h100.sh

EXPOSE 8000  # vLLM 默认端口

# TODO: 添加模型权重下载逻辑（DeepSeek-V4-Flash 权重）
# ENV MODEL权重_URL=...

ENTRYPOINT ["/app/launch_h100.sh"]
