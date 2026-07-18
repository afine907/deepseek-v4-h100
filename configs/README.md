# 配置目录

> ⏳ 本目录文件为占位符，将在代码开发阶段逐步填充。

## 目录结构

| 文件 | 说明 |
|------|------|
| `kv_cache.yaml` | KV Cache LRU 淘汰策略配置 |
| `batching.yaml` | 批处理调度配置（Continuous Batching / Chunked Prefill） |
| `model.yaml` | 模型配置（TP=8、FP8 量化） |
| `scheduler.yaml` | 调度器配置（超时、并发数） |

## 参数来源

| 参数 | 值 | 决策来源 |
|------|---|---------|
| `kv_cache.high_watermark` | 0.90 | `docs/brainstorming/02-kv-cache-lfu.md` |
| `kv_cache.low_watermark` | 0.75 | `docs/brainstorming/02-kv-cache-lfu.md` |
| `chunked_prefill.chunk_size` | 512 | `docs/brainstorming/03-chunked-prefill-assumption.md` |
| `batching.max_batch_size` | 32 | `docs/brainstorming/06-tp8-nccl.md` |
| `batching.prefill_ratio` | 0.3 | `docs/brainstorming/06-tp8-nccl.md` |
| `model.tensor_parallel_size` | 8 | 比赛要求 |
| `model.quantization` | FP8 | 比赛要求 |
