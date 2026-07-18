# 实验复现文档

> ⏳ 本文件为占位符模板，将在基线测试完成后填充真实数据。

---

## 一、环境设置

### 1.1 硬件环境

- GPU：8× NVIDIA H100 (80GB)
- NVLink 全互联
- CUDA 12.x

### 1.2 软件环境

- Docker
- 镜像：`deepseek-v4-h100:latest`

### 1.3 构建镜像

```bash
docker build -t deepseek-v4-h100 .
```

---

## 二、基线运行（未优化）

### 2.1 启动基线服务

```bash
bash launch_h100.sh \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90
```

### 2.2 运行 SWE-bench 评测

```bash
python tests/benchmark_swe.py \
  --dataset swebench.harness.run_task.HarnessTask \
  --output baseline_results.json
```

### 2.3 基线性能数据（⚠️ 待实测）

| 指标 | 基线值 |
|------|--------|
| P50 延迟 | ? s |
| P90 延迟 | ? s |
| P99 延迟 | ? s |
| QPS | ? |
| GPU 利用率 | ? % |
| KV Cache 命中率 | ? % |
| SWE-bench 完成率 | ? % |

---

## 三、优化运行

### 3.1 启动优化服务

```bash
bash launch_h100.sh \
  --model deepseek-v4-flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90
# 加载优化配置（TODO: 配置文件加载机制）
```

### 3.2 运行 SWE-bench 评测

```bash
python tests/benchmark_swe.py \
  --dataset swebench.harness.run_task.HarnessTask \
  --output optimized_results.json
```

### 3.3 优化性能数据（⚠️ 待实测）

| 指标 | 优化值 |
|------|--------|
| P50 延迟 | ? s |
| P90 延迟 | ? s |
| P99 延迟 | ? s |
| QPS | ? |
| GPU 利用率 | ? % |
| KV Cache 命中率 | ? % |
| SWE-bench 完成率 | ? % |

---

## 四、性能对比

### 4.1 对比表

```
┌───────────────┬─────────────┬─────────────┬─────────┐
│ 指标           │ 基线         │ 优化后       │ 提升    │
├───────────────┼─────────────┼─────────────┼─────────┤
│ P99 延迟       │ ? s         │ ? s         │ ? %    │
│ QPS            │ ?           │ ?           │ ? %    │
│ GPU 利用率     │ ? %         │ ? %         │ ? pp   │
│ KV Cache 命中率 │ ? %         │ ? %         │ ? pp   │
│ SWE-bench 完成率│ ? %        │ ? %         │ ? pp   │
└───────────────┴─────────────┴─────────────┴─────────┘
```

### 4.2 关键优化点效果分析

- **KV Cache LRU**：对长尾请求的缓存命中效果
- **Chunked Prefill**：对长输入请求的延迟改善
- **Continuous Batching**：对 QPS 和 GPU 利用率的提升

---

## 五、已知问题

- [ ] 基线数据待实测后填充
- [ ] DeepSeek-V4-Flash 模型权重获取方式待确认
- [ ] SWE-bench 数据集准备
