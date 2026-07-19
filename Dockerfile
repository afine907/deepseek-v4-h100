# DeepSeek-V4-Flash 8×H100 推理容器镜像
# 参考: docs/original-requirements.md, docs/competition-document.md

FROM nvidia/cuda:12.4.1-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV VLLM_ENABLE_V1_MULTIPROCESSING=0

# 安装基础依赖
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip git curl \
    && rm -rf /var/lib/apt/lists/*

# 设置 Python 3.10
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.10 1

# 安装 PyTorch (CUDA 12.4)
RUN pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124

# 安装 vLLM GPU 版
RUN pip install vllm>=0.6.0

# 安装项目依赖
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制源码
COPY src/ /app/src/
COPY configs/ /app/configs/

# NCCL 环境变量（参考 docs/brainstorming/06-tp8-nccl.md）
ENV NCCL_MIN_NCHANNELS=8
ENV NCCL_MAX_NCHANNELS=16
ENV NCCL_IB_TIMEOUT=20
ENV NCCL_IB_RETRY_CNT=7

# 暴露端口
EXPOSE 8000  # vLLM / tuner server
EXPOSE 8001  # metrics

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/status')" || exit 1

# 入口点
ENTRYPOINT ["python", "/app/src/main.py"]
CMD ["--mode", "server"]
