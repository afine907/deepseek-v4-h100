B# 复盘：单元测试全面重写 + P0 Bug 修复

## 时间
2026-07-19 22:53

## 背景
CODE_QUALITY_REPORT 指出 21 个测试失败 + 多个 P0 Bug。用户要求修复测试并处理报告中的问题。

## 根因

**测试弱断言** — 原测试只验证"不崩溃"，不验证行为正确性：
- `assert evicted >= 0`（永远成立）
- `assert 0.0 <= rate <= 1.0`（永远成立）
- `assert len(results) >= 0`（永远成立）

**未理解被测系统实际行为**就写断言：
1. 以为 `evict_if_needed()` 是唯一触发点 → 实际 eviction 在 `record_access()` miss 路径中已触发
2. 以为 watermark == 触发 → 实际是 `>=` 而非 `>`
3. 以为 `p50` 取下中位数 → 实际取上中位数（偶数长度）
4. 以为 MockInferenceEngine 在 `step()` 中完成 → 实际依赖后台线程 + wall-clock 时钟
5. `current_chunk` 从不递增（scheduler bug）
6. `decode_slots` 用错变量 `prefill_count=0` 而非 `running_prefill`

## 修复内容

| 类型 | 文件 | 内容 |
|------|------|------|
| P0 Bug | scheduler.py | current_chunk 递增、decode_slots 修正 |
| P0 Bug | kv_cache_manager.py | set_max_blocks 加锁 |
| P1 Bug | vllm_adapter.py | 异常吞噬 → logger |
| P1 Bug | tuner_server.py | F821 类型修复 |
| P1 Bug | reporter.py | f-string 语法修复 |
| 测试重写 | test_kv_cache_manager.py | 28 tests，LRU/watermark/max_evict/并发 |
| 测试重写 | test_scheduler.py | 20 tests，SJF/chunks/prefill_ratio |
| 测试重写 | test_mock_adapter.py | 16 tests，精确断言 |
| 测试补强 | test_adapters.py | 并发/超时 9 tests |

**结果**: 132 passing, 0 failing

## 关键教训

1. **先诊断，后断言** — 写测试前必须用 `python -c` 单独验证目标行为
2. **Mock ≠ 真实实现** — 两者行为可能不同，要分别验证
3. **数据结构方法要实测** — `popitem()` / `len()` / 中位计算都要先验证
4. **后台线程时钟敏感** — MockInferenceEngine 依赖 wall-clock，需要 `time.sleep()` 让其完成

## 来源
本次会话，Claude Code session
