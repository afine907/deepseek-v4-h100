# 架构图集

> 本文件包含系统架构的 Mermaid 源码，可直接在 GitHub/GitLab/Docusaurus 中渲染。

---

## 图 1：四层架构总览

```mermaid
graph TB
    subgraph Control["控制层"]
        AT[自动调优器<br/>Auto-Tuner]
    end

    subgraph Routing["路由与调度层"]
        SG[调度器<br/>Scheduler]
        CP[Chunked Prefill<br/>分块预填充]
        BATCH[Continuous Batching<br/>连续批处理]
    end

    subgraph Engine["推理引擎层"]
        VLLM[vLLM Engine<br/>FP8 / TP=8]
        KVM[KV Cache 管理器<br/>LRU 淘汰]
    end

    subgraph Observability["可观测层"]
        PM[Prometheus<br/>Metrics]
        H[健康检查<br/>/health]
    end

    AT -->|调参| SG
    SG --> CP
    SG --> BATCH
    CP --> VLLM
    BATCH --> VLLM
    VLLM --> KVM
    VLLM --> PM
    VLLM --> H
```

---

## 图 2：请求处理时序

```mermaid
sequenceDiagram
    participant C as 客户端
    participant S as 调度器
    participant CP as Chunked Prefill
    participant V as vLLM Engine
    participant KVM as KV Cache (LRU)
    participant M as Prometheus

    C->>S: 推理请求
    S->>S: 长度检查 + 截断
    S->>CP: 提交请求

    Note over CP: 长请求切分为 512-token 块
    CP->>V: Chunk 1 (tokens 0-512)
    V->>KVM: 写入 KV Cache
    KVM->>KVM: LRU 淘汰检查

    CP->>V: Chunk 2 (tokens 512-1024)
    V->>KVM: 写入 + 淘汰
    CP->>V: Chunk N...

    V->>M: latency_ms, gpu_memory_bytes
    V-->>S: 推理结果
    S-->>C: 响应
```

---

## 图 3：LRU 淘汰流程

```mermaid
flowchart LR
    A[请求完成<br/>写入 KV Cache] --> B{显存使用率}
    B -->|≤ 90%| OK[正常保留]
    B -->|> 90%| C[触发 LRU 淘汰]
    C --> D[按最后访问时间排序]
    D --> E[淘汰最老的 block]
    E --> F{显存 < 75% ?}
    F -->|否| E
    F -->|是| OK
```

---

## 图 4：TP=8 分布式架构

```mermaid
graph LR
    subgraph H100_Cluster["8×H100 NVLink 集群"]
        G0[GPU 0]
        G1[GPU 1]
        G2[GPU 2]
        G3[GPU 3]
        G4[GPU 4]
        G5[GPU 5]
        G6[GPU 6]
        G7[GPU 7]
    end

    subgraph MoE_AlltoAll["MoE All-to-All 通信"]
        A2A[All-to-All<br/>8卡路由]
    end

    VLLM[vLLM] --> A2A
    A2A --> G0
    A2A --> G1
    A2A --> G2
    A2A --> G3
    A2A --> G4
    A2A --> G5
    A2A --> G6
    A2A --> G7
```

---

## 图 5：Continuous Batching 调度

```mermaid
gantt
    title Continuous Batching 调度示意
    dateFormat X
    axisFormat %s s

    section Batch 1
    ReqA :0, 15
    ReqB :0, 15
    ReqC :0, 15
    ReqD :0, 15

    section Batch 2
    ReqE :16, 28
    ReqF :16, 28
    ReqG :16, 28
    ReqH :16, 28
```

---

## 图 6：优化前后延迟对比

```mermaid
xychart-beta
    title "P99 延迟对比（假设）"
    x-axis [基线, 优化后]
    y-axis "延迟 (s)" 0 --> 12
    bar [10, 4.5]
    line [10, 4.5]
```

> ⚠️ 基线为假设值，待实测后更新。

---

## 图 7：模块依赖关系

```mermaid
graph TD
    subgraph src["src/"]
        AE[auto_tuner.py]
        SE[scheduler.py]
        KE[kv_cache_manager.py]
        IE[inference_engine.py]
        ME[metrics_exporter.py]
    end

    subgraph configs["configs/"]
        MC[model.yaml]
        BC[batching.yaml]
        KC[kv_cache.yaml]
    end

    AE -->|UpdateConfig| SE
    SE --> KE
    SE --> IE
    IE --> ME
    SE -->|chunk_size| KC
    SE -->|batch_size| BC
    AE -->|tensor_parallel| MC
```
