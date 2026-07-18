#!/bin/bash
# DeepSeek-V4-Flash 8×H100 一键启动脚本
# 参考: docs/competition-document.md §六、交付物清单

set -e

# 默认参数
MODEL="deepseek-v4-flash"
TP_SIZE=8
GPU_MEM_UTIL=0.90
PORT=8000

# 参数解析
while [[ $# -gt 0 ]]; do
    case $1 in
        --model)
            MODEL="$2"
            shift 2
            ;;
        --tensor-parallel-size)
            TP_SIZE="$2"
            shift 2
            ;;
        --gpu-memory-utilization)
            GPU_MEM_UTIL="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--model MODEL] [--tensor-parallel-size N] [--gpu-memory-utilization FLOAT] [--port N]"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "=========================================="
echo "  DeepSeek-V4-Flash 推理服务启动"
echo "=========================================="
echo "  模型: $MODEL"
echo "  TP size: $TP_SIZE"
echo "  GPU 显存利用率: $GPU_MEM_UTIL"
echo "  端口: $PORT"
echo "=========================================="

# TODO: 模型权重检查
# TODO: DeepSeek-V4-Flash 权重路径配置
# MODEL_PATH="${MODEL_DIR}/${MODEL}"

# 启动 vLLM
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --tensor-parallel-size "$TP_SIZE" \
    --gpu-memory-utilization "$GPU_MEM_UTIL" \
    --port "$PORT" \
    --trust-remote-code \
    --quantization FP8 \
    2>&1 | tee /var/log/vllm.log
