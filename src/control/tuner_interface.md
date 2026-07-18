# control/tuner_interface.py — 调参接口（Mock）

> ⏳ 本模块为占位符，参赛版仅做 Mock 实现。

---

## 模块职责

`tuner_interface.py` 是控制层的预留接口，**参赛版不做真实调参闭环**（4 小时赛程内不启用），仅提供：

1. **gRPC 服务端**（Mock）— 接收 `UpdateConfig` / `GetStatus` 调用
2. **配置存储** — 内存中的配置快照
3. **日志记录** — 记录收到的调参指令（供赛后分析）

---

## Proto 定义

```protobuf
// scheduler_control.proto
service SchedulerControl {
  rpc UpdateConfig(UpdateConfigRequest) returns (UpdateConfigResponse);
  rpc GetStatus(GetStatusRequest) returns (GetStatusResponse);
}

message UpdateConfigRequest {
  int32 batch_size = 1;
  int32 chunk_size = 2;
  float kv_cache_high_watermark = 3;
  float kv_cache_low_watermark = 4;
  int32 max_concurrent_requests = 5;
}

message UpdateConfigResponse {
  bool success = 1;
  string message = 2;
  Config applied_config = 3;
}
```

---

## 公开接口（Mock 实现）

```python
class MockTunerInterface:
    """Mock 调参接口，参赛版使用。"""

    def update_config(
        self,
        batch_size: Optional[int] = None,
        chunk_size: Optional[int] = None,
        kv_cache_high_watermark: Optional[float] = None,
        kv_cache_low_watermark: Optional[float] = None,
    ) -> bool:
        """更新调度参数（内存中，不影响实际运行）。"""
        logger.info("MockTuner: update_config called (not applied)")
        return True

    def get_status(self) -> dict:
        """返回当前配置快照（Mock）。"""
        return {
            "batch_size": 32,
            "chunk_size": 512,
            "kv_cache_high_watermark": 0.90,
            "kv_cache_low_watermark": 0.75,
        }
```

---

## 与调度层的交互

Mock 实现中，`tuner_interface.py` **不实际修改** `scheduler.py` 或 `kv_cache_manager.py` 的配置。
真实调参需要通过：
1. 轮询 Prometheus metrics
2. 分析瓶颈
3. 调用 `update_config()`
4. 观察效果

**参赛版跳过此闭环**，专注调度和推理优化。

---

## 真实 gRPC 实现（未来扩展）

如需真实实现：

```python
import grpc
from concurrent import futures

class TunerServicer(SchedulerControlServicer):
    def UpdateConfig(self, request, context):
        # 更新 configs/ 中的 YAML 文件
        # 通知 scheduler.py 热重载
        pass

    def GetStatus(self, request, context):
        # 从 scheduler.py 收集状态
        pass
```

---

## 配置参数

| 参数 | 默认值 |
|------|--------|
| `batch_size` | 32 |
| `chunk_size` | 512 |
| `kv_cache_high_watermark` | 0.90 |
| `kv_cache_low_watermark` | 0.75 |
| `max_concurrent_requests` | 128 |

---

## 测试

```bash
pytest tests/unit/test_tuner_interface.py -v
```

---

## 状态

⏳ **待实现** — Proto 定义见 [docs/brainstorming/04-api-contracts.md](../docs/brainstorming/04-api-contracts.md)
