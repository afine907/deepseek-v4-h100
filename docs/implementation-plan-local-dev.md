# 实现计划：DeepSeek-V4-Flash 推理优化系统 — 本地开发 + Agent 调优

> **版本：** v1.0
> **日期：** 2026-07-18
> **状态：** ⚠️ **已过时** — 请参考 [LOCAL_DEV_PLAN.md](LOCAL_DEV_PLAN.md) 获取最新方案

---

## 一、背景与目标

项目当前处于纯文档阶段（12 个 `.md` 文件），没有任何源代码。由于 H100 机器需要到比赛测试阶段才能使用，因此需要在 **WSL2 (Ubuntu 22.04, CPU-only, 16核/12GB)** 环境中先跑通核心调优代码。

**最终目标：** 在 8×H100 上运行 DeepSeek-V4-Flash (FP8, TP=8)，核心调度/缓存/调优逻辑必须在本地可验证。

**用户选定的方案：**
- 开发环境：WSL2 全环境（vLLM CPU-only + Qwen3.5-0.8B），WSL2 内存上限保持 12GB，不修改 `.wslconfig`
- 测试模型：Qwen3.5-0.8B（CPU 上用于功能/链路验证）
- 调优方式：LLM Agent 驱动（接入 Claude/GPT API 做自优化循环）
- 架构：六边形架构（Ports & Adapters），核心调优代码与具体推理后端解耦

---

## 二、架构设计

### 2.1 六边形架构概览

```
                    ┌──────────────────────┐
                    │   LLM Agent Tuner    │  ← AI 驱动的自优化
                    └──────────┬───────────┘
                               │ REST API (内部 HTTP)
                    ┌──────────▼───────────┐
                    │    Control Layer     │
                    │  (Tuner Interface)   │
                    └──────────┬───────────┘
                               │
┌──────────────────────────────────────────────────────────────┐
│                         Core Domain                          │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Scheduler (Port interface)               │  │
│  │  - Chunked Prefill                                   │  │
│  │  - Continuous Batching                               │  │
│  │  - Priority Queue (SJF + aging)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        InferenceEngine (Port interface)                │  │
│  │  submit() / get_result() / cancel() / status()        │  │
│  └───────┬───────────────────────────────┬──────────────┘  │
│          │                               │                  │
│  ┌───────▼──────────┐          ┌────────▼─────────┐     │
│  │ vLLM Adapter     │          │ Mock Adapter     │     │
│  │ (WSL2 / H100)   │          │ (Unit Test)     │     │
│  └──────────────────┘          └──────────────────┘     │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           KV Cache Manager (Port interface)            │  │
│  │  - LRU Eviction                                      │  │
│  │  - Block-level Management                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │           Metrics Collector (Port interface)            │  │
│  │  - Latency histograms / Throughput counters            │  │
│  │  - Cache hit rate                                     │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 核心设计原则

1. **InferenceEngine 是端口（抽象接口）**，vLLM Adapter 和 Mock Adapter 是具体实现
2. **Scheduler 依赖 InferenceEngine 接口**，不依赖具体推理引擎
3. **KV Cache Manager 独立于推理引擎**，可被 Scheduler 直接调用
4. **Metrics Collector 统一采集**，各层通过回调上报
5. **LLM Agent Tuner** 通过 REST API 读取 metrics 并下发调参指令

### 2.3 配置驱动切换

| 环境 | backend | model | tp | 量化 |
|------|---------|-------|----|------|
| WSL2 (CPU) | vllm_cpu | Qwen/Qwen3.5-0.8B | 1 | bfloat16 |

> 本地资源护栏：WSL2 保持 12GB 内存上限，不修改 `.wslconfig`；Qwen3.5-0.8B 使用 Gated DeltaNet + MoE 架构，支持 `bfloat16`（本机具备 `avx512_bf16`），0.8B 模型权重远小于 2B 版本，KV Cache 可用空间大幅增加。推荐配置：`max_model_len=8192`、`max_num_seqs=8`、`gpu_memory_utilization=0.60`、`kv_cache_memory_bytes=536870912`（512MB）、`OMP_NUM_THREADS=12`、`MKL_NUM_THREADS=12`。本地只验收功能、稳定性与指标链路，不用其吞吐/延迟对标 H100。
| H100 (生产) | vllm | deepseek-ai/DeepSeek-V4-Flash | 8 | fp8 |

切换方式：修改 `configs/model.yaml`，核心代码零改动。

---

## 三、项目结构

```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── ports.py              # 所有端口接口定义
│   ├── models.py             # 数据模型（InferenceRequest, Response, etc.）
│   ├── scheduler.py           # Chunked Prefill + Continuous Batching
│   └── kv_cache_manager.py    # LRU 淘汰管理器
├── adapters/
│   ├── __init__.py
│   ├── vllm_adapter.py       # vLLM 推理引擎适配器
│   ├── mock_adapter.py       # Mock 引擎适配器（测试用）
│   └── metrics.py            # Prometheus 格式指标导出
├── control/
│   ├── __init__.py
│   ├── tuner_interface.py    # 调参接口（REST API）
│   └── tuner_server.py       # FastAPI 控制层服务器
├── agent/
│   ├── __init__.py
│   ├── tuner_agent.py        # LLM Agent 调优主逻辑
│   └── prompts.py            # Agent prompt 模板
├── config/
│   └── settings.py           # 配置加载（YAML/环境变量）
└── main.py                   # 入口：启动服务或交互式评测

configs/
├── model.yaml                # 模型配置
├── batching.yaml             # 批处理配置
├── kv_cache.yaml            # KV Cache 配置
└── agent.yaml                # Agent 调优配置

tests/
├── unit/
│   ├── test_scheduler.py
│   ├── test_kv_cache.py
│   └── test_adapters.py
└── integration/
    └── test_full_pipeline.py
```

---

## 四、实施步骤

### Phase 1：WSL2 环境准备

**目标：** 在 WSL2 中安装 vLLM (CPU mode) + Qwen3.5-0.8B，验证单条推理能跑通。

**步骤：**

1. 启动 WSL2 Ubuntu-22.04，更新 apt 包
2. 安装 Python 3.10 开发依赖（pip, venv）
3. 创建项目虚拟环境 `~/deepseek-local/venv`
4. 安装 PyTorch (CPU-only): `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu`
5. 安装 transformers + accelerate + sentencepiece
6. 安装 vLLM (CPU backend): `pip install vllm`
7. 下载 Qwen3.5-0.8B（HuggingFace）
8. 在 12GB WSL2 内存预算内，设置 `OMP_NUM_THREADS=12`、`MKL_NUM_THREADS=12`、`dtype=bfloat16`、`max_model_len=8192`、`max_num_seqs=8`、`gpu_memory_utilization=0.60`、`kv_cache_memory_bytes=536870912` 并完成单请求生成验证

```bash
export OMP_NUM_THREADS=12 MKL_NUM_THREADS=12 TOKENIZERS_PARALLELISM=false
python -c "from vllm import LLM, SamplingParams; \
  llm = LLM(model='Qwen/Qwen3.5-0.8B', dtype='bfloat16', tensor_parallel_size=1, max_model_len=8192, max_num_seqs=8, gpu_memory_utilization=0.60, kv_cache_memory_bytes=536870912, enforce_eager=True); \
  print(llm.generate(['Hello'], SamplingParams(max_tokens=10, temperature=0.0)))"
```

**WSL2 环境规格：**
- OS: Ubuntu 22.04.5 LTS
- CPU: AMD Ryzen 7 H 255 (16核)
- 内存: 12GB
- 磁盘: 953GB 可用
- Python: 3.10.12

---

### Phase 2：核心代码实现

**目标：** 实现六边形架构的核心接口和基本实现，跑通 Scheduler → Engine → Response 完整链路。

#### 2.1 端口接口 (`src/core/ports.py`)

```python
class InferenceEngine(ABC):
    """推理引擎端口 — 所有 Adapter 必须实现"""
    @abstractmethod
    def submit(self, request: InferenceRequest) -> str: ...

    @abstractmethod
    def get_result(self, request_id: str, timeout: float) -> InferenceResponse: ...

    @abstractmethod
    def cancel(self, request_id: str) -> bool: ...

    @abstractmethod
    def get_status(self) -> EngineStatus: ...


class SchedulerPort(ABC):
    """调度器端口"""
    @abstractmethod
    def enqueue(self, request: InferenceRequest) -> str: ...

    @abstractmethod
    def step(self) -> list[InferenceResponse]: ...

    @abstractmethod
    def get_queue_status(self) -> QueueStatus: ...


class KVCacheManagerPort(ABC):
    """KV Cache 管理器端口"""
    @abstractmethod
    def evict_if_needed(self) -> int: ...

    @abstractmethod
    def record_access(self, block_id: str): ...

    @abstractmethod
    def get_hit_rate(self) -> float: ...
```

#### 2.2 调度器 (`src/core/scheduler.py`)

**核心功能：**
- **Chunked Prefill**：长输入切 512 tokens/块，逐块 prefill，不阻塞 Decode
- **Continuous Batching**：max_batch_size=32, prefill_ratio=0.3
- **SJF + aging 反饥饿**：

```
调度优先级 = request_remaining_tokens / (1 + wait_time × 0.1)
```

- 调用 `InferenceEngine.submit()` 进行实际推理
- 调用 `KVCacheManagerPort.evict_if_needed()` 管控显存
- 调用 `MetricsCollector` 记录延迟/吞吐/QPS

#### 2.3 KV Cache 管理器 (`src/core/kv_cache_manager.py`)

- **Block-level LRU 淘汰**
- 高水位 90% 触发，低水位 75% 停止
- 单轮最多淘汰 50 个 block
- 按最后访问时间排序，淘汰最久未访问的 block
- 统计命中率

#### 2.4 vLLM Adapter (`src/adapters/vllm_adapter.py`)

- 封装 `vllm.LLM` 或 `vllm.AsyncLLMEngine`
- WSL2 模式：CPU backend，Qwen3.5-0.8B，TP=1，`max_model_len=8192`，`max_num_seqs=8`
- H100 生产模式：GPU，DeepSeek-V4-Flash，TP=8，FP8
- 通过配置切换 adapter

#### 2.5 Mock Adapter (`src/adapters/mock_adapter.py`)

- 模拟推理延迟（均匀/正态分布）
- 模拟 KV Cache 行为
- 用于单元测试，不依赖 vLLM

#### 2.6 指标采集 (`src/adapters/metrics.py`)

基于 Prometheus client，暴露：
- `inference_latency_ms` (Histogram)
- `requests_total` / `tokens_generated_total` (Counter)
- `gpu_memory_used_bytes` (Gauge)
- `kv_cache_hit_rate` (Gauge)
- `queue_length` / `active_requests` (Gauge)

#### 2.7 控制层 (`src/control/tuner_server.py`)

FastAPI 服务，提供 REST API：
- `GET /status` — 当前系统状态
- `POST /config` — 更新参数
- `GET /metrics` — Prometheus 指标
- `POST /reset` — 重置统计

---

### Phase 3：LLM Agent 调优

**目标：** 构建 AI Agent，自动分析指标、决策调参、迭代优化。

#### 3.1 工作流程

```
┌─────────┐    ┌──────────┐    ┌──────────┐    ┌─────────┐
│ 基准测试 │───→│ 采集指标  │───→│ Agent    │───→│ 更新配置 │
│ (SWE模拟)│    │ (metrics)│    │ 分析决策  │    │ (params) │
└─────────┘    └──────────┘    └──────────┘    └─────────┘
                                   ↑                │
                                   │    ┌──────────┐ │
                                   └────│ 迭代检查 │←┘
                                        │ (收敛?)  │
                                        └──────────┘
```

#### 3.2 Agent 核心逻辑 (`src/agent/tuner_agent.py`)

1. **Analysis Phase**：读取当前 metrics（P50/P90/P99 延迟、QPS、命中率、GPU 利用率）
2. **Decision Phase**：调用 LLM API（Claude 或 GPT），传入当前性能数据和配置，LLM 输出推荐参数变化
3. **Apply Phase**：更新配置，重启/热加载 benchmark
4. **Measure Phase**：重新运行 benchmark，采集新指标
5. **Compare Phase**：对比前后指标，判断是否收敛
6. **Loop**：最多 N 轮（默认 10 轮），或连续 3 轮无明显提升则停止

#### 3.3 Agent Prompt 设计 (`src/agent/prompts.py`)

System prompt 包含：
- 当前系统架构描述
- 可调参数范围（batch_size=[8,64], chunk_size=[256,2048], watermark_high=[0.85,0.95], etc.）
- 优化目标（P99<5s, QPS>100, GPU>80%, Cache>70%）
- 输出格式约束（JSON：`{"changes": {...}, "reasoning": "..."}`）

历史记录作为 context（最近 3 轮结果），防止来回震荡。

#### 3.4 容错设计

- Agent 输出解析失败 → 重试（最多 3 次）/ 回退到保守参数
- API 调用超时 → 使用本地启发式作为 fallback
- 单次 benchmark 失败 → 跳过该轮，记录错误

---

### Phase 4：本地验证

**目标：** 在 WSL2 中用 Qwen3.5-0.8B 跑通全流程。

测试场景：

| 模式 | 说明 | 验证内容 |
|------|------|---------|
| Mock 模式 | 不装 vLLM，用 Mock Adapter | 调度逻辑正确性 |
| vLLM CPU 模式 | Qwen3.5-0.8B，小批量请求 | 框架联通性 |
| 批量压测 | 模拟 SWE-bench 负载 | Chunked Prefill + Continuous Batching |

**Mock 模式验证（立即可测）：**
```bash
python src/main.py --mode mock --benchmark tests/data/swe_sample.json
```

**vLLM CPU 模式验证：**
```bash
python src/main.py --mode vllm_cpu --model Qwen/Qwen3.5-0.8B-Instruct
```

**Agent 调优模式：**
```bash
python src/main.py --mode tune --agent --max-iterations 10
```

---

### Phase 5：生产切换

**目标：** 确保从本地 WSL2 无缝切换到 H100 生产环境。

切换方式：修改 `configs/model.yaml`：

```yaml
# WSL2 (CPU)
model:
  backend: vllm_cpu
  name: Qwen/Qwen3.5-0.8B-Instruct
  tensor_parallel_size: 1
  dtype: float32

# H100 (生产)
model:
  backend: vllm
  name: deepseek-ai/DeepSeek-V4-Flash
  tensor_parallel_size: 8
  quantization: fp8
```

核心调度/缓存/调优代码 **零改动**。

---

## 五、关键文件清单

| 文件 | 说明 |
|------|------|
| `src/core/ports.py` | 所有端口接口定义 |
| `src/core/models.py` | 数据模型定义 |
| `src/core/scheduler.py` | 核心调度器 |
| `src/core/kv_cache_manager.py` | KV Cache LRU 管理 |
| `src/adapters/vllm_adapter.py` | vLLM 适配器 |
| `src/adapters/mock_adapter.py` | Mock 适配器 |
| `src/adapters/metrics.py` | 指标采集 |
| `src/control/tuner_server.py` | 控制层 REST API |
| `src/control/tuner_interface.py` | 调参接口抽象 |
| `src/agent/tuner_agent.py` | LLM Agent 调优逻辑 |
| `src/agent/prompts.py` | Agent prompt 模板 |
| `src/config/settings.py` | 配置加载 |
| `src/main.py` | 入口 |
| `configs/model.yaml` | 模型配置 |
| `configs/batching.yaml` | 批处理配置 |
| `configs/kv_cache.yaml` | KV Cache 配置 |
| `configs/agent.yaml` | Agent 调优配置 |
| `tests/unit/*.py` | 单元测试 |
| `tests/integration/test_full_pipeline.py` | 集成测试 |
| `requirements.txt` | Python 依赖 |

---

## 六、验证方案

### Phase 1 验证
```bash
export OMP_NUM_THREADS=12 MKL_NUM_THREADS=12 TOKENIZERS_PARALLELISM=false
python -c "from vllm import LLM, SamplingParams; \
  llm = LLM(model='Qwen/Qwen3.5-0.8B', dtype='bfloat16', tensor_parallel_size=1, max_model_len=8192, max_num_seqs=8, gpu_memory_utilization=0.60, kv_cache_memory_bytes=536870912, enforce_eager=True); \
  print(llm.generate(['Hello'], SamplingParams(max_tokens=10, temperature=0.0)))"
```

### Phase 2+3 验证
```bash
# Mock 模式（无需 vLLM）
python src/main.py --mode mock --benchmark tests/data/swe_sample.json

# Agent 自动调优模式
python src/main.py --mode tune --agent --max-iterations 10
```

### 单元测试
```bash
pytest tests/unit/ -v --cov=src
```

### 集成测试
```bash
pytest tests/integration/ -v
```

---

## 七、依赖包

```
torch>=2.0.0
transformers>=4.40.0
accelerate>=0.25.0
sentencepiece>=0.1.99
vllm>=0.4.0
prometheus-client>=0.19.0
fastapi>=0.110.0
uvicorn>=0.27.0
pydantic>=2.0.0
pyyaml>=6.0.0
anthropic>=0.18.0
openai>=1.0.0
pytest>=8.0.0
pytest-cov>=4.0.0
```

---

## 七、H100 生产环境验证

### 构建并启动
```bash
# 构建镜像
docker build -t deepseek-v4-h100 .

# 一键启动
bash launch_h100.sh \
  --model deepseek-ai/DeepSeek-V4-Flash \
  --tensor-parallel-size 8 \
  --gpu-memory-utilization 0.90 \
  --port 8000

# 或切换配置文件后启动
cp configs/model.h100.yaml configs/model.yaml
docker run --gpus all --shm-size=64g -p 8000:8000 deepseek-v4-h100
```

### H100 生产环境验证目标

| 指标 | 目标 | 测量方法 |
|------|------|---------|
| P99 延迟 | < 5.0s | SWE-bench 基准测试 |
| QPS | > 100 | 负载测试工具（wrk/locust） |
| GPU 利用率 | > 80% | `nvidia-smi` 或 Prometheus |
| KV Cache 命中率 | > 70% | `/metrics` 端点 |
| SWE-bench 完成率 | > 99% | 基准测试脚本 |

### 验证命令
```bash
# 1. 检查 GPU 利用率
nvidia-smi

# 2. 检查 metrics 端点
curl http://localhost:8000/metrics

# 3. 检查服务状态
curl http://localhost:8000/status

# 4. 发送推理请求测试
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"prompt": "def hello():", "max_tokens": 50}'

# 5. 运行完整 SWE-bench 评测
python tests/benchmark_swe.py --output results.json
```
