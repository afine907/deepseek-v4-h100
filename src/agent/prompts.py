"""Agent prompt templates for LLM-based tuning decisions."""

ANALYSIS_PROMPT = """\
You are an AI inference system tuning agent.

Current system metrics:
- P50 latency: {p50_ms}ms
- P90 latency: {p90_ms}ms
- P99 latency: {p99_ms}ms
- QPS: {qps}
- KV Cache hit rate: {cache_hit_rate}
- GPU utilization: {gpu_util}

Current configuration:
{config_str}

Optimization targets:
- P99 latency < 5000ms
- QPS > 100
- GPU utilization > 80%
- KV Cache hit rate > 70%

Available parameters to tune (with safe ranges):
- batch_size: [8, 64] (current: {batch_size})
- chunk_size: [256, 2048] tokens (current: {chunk_size})
- kv_cache_high_watermark: [0.85, 0.95] (current: {kv_cache_high_watermark})
- prefill_ratio: [0.1, 0.5] (current: {prefill_ratio})

History (last 3 rounds):
{history}

Output your analysis and recommended changes in JSON format:
{{"changes": {{"param": "new_value", ...}}, "reasoning": "why these changes"}}\
"""

DECISION_PROMPT = """\
Given the following agent recommendations over {n_rounds} rounds:
{recommendations}

And the actual results after applying those changes:
{results}

Should we continue tuning or stop? Output in JSON:
{{"decision": "continue" | "stop", "reasoning": "...", "final_config": {{...}}}}\
"""
