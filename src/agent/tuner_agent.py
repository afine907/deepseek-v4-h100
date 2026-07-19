"""LLM-driven automatic tuning agent."""

import json
import logging
import os
from dataclasses import dataclass

from .benchmark_runner import BenchmarkRunner
from .prompts import ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class TuningHistory:
    """Record of one tuning round."""

    round_num: int
    config: dict
    metrics_before: dict
    metrics_after: dict
    changes: dict
    reasoning: str


@dataclass
class TuningResult:
    """Result of a full tuning run."""

    converged: bool
    final_config: dict
    total_rounds: int
    history: list[TuningHistory]


class TunerAgent:
    """
    LLM-driven automatic tuning agent:
    1. Measure: run benchmark and collect metrics
    2. Analysis: call LLM to analyze and decide parameter changes
    3. Apply: update configuration via tuner interface
    4. Measure again: re-run benchmark after changes
    5. Compare: check convergence
    """

    def __init__(
        self,
        tuner_interface,
        benchmark_runner: BenchmarkRunner,
        config: dict,
        max_iterations: int = 10,
        convergence_threshold: float = 0.05,
        llm_provider: str = "mock",
        llm_api_key: str | None = None,
        llm_model: str = "claude-sonnet-4-20250514",
    ):
        self._tuner = tuner_interface
        self._runner = benchmark_runner
        self._config = config
        self._max_iterations = max_iterations
        self._threshold = convergence_threshold
        self._llm_provider = llm_provider
        self._llm_api_key = (
            llm_api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("OPENAI_API_KEY")
        )
        self._llm_model = llm_model
        self._history: list[TuningHistory] = []

    def _call_llm(self, prompt: str) -> dict:
        """Call LLM API (Claude / OpenAI / Mock)."""
        if self._llm_provider == "mock":
            return self._mock_llm_response(prompt)
        elif self._llm_provider == "claude":
            return self._call_claude(prompt)
        elif self._llm_provider == "openai":
            return self._call_openai(prompt)
        raise ValueError(f"Unknown LLM provider: {self._llm_provider}")

    def _mock_llm_response(self, prompt: str) -> dict:
        """Deterministic mock LLM response for testing."""
        return {
            "changes": {"batch_size": 24, "kv_cache_high_watermark": 0.90},
            "reasoning": "Mock: deterministic response for testing",
        }

    def _call_claude(self, prompt: str) -> dict:
        """Call Anthropic Claude API."""

        import anthropic

        client = anthropic.Anthropic(api_key=self._llm_api_key)
        response = client.messages.create(
            model=self._llm_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        return self._parse_llm_json(text)

    def _call_openai(self, prompt: str) -> dict:
        """Call OpenAI Chat API."""
        import openai

        client = openai.OpenAI(api_key=self._llm_api_key)
        response = client.chat.completions.create(
            model=self._llm_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        text = response.choices[0].message.content
        return self._parse_llm_json(text)

    def _parse_llm_json(self, text: str) -> dict:
        """Parse JSON from LLM response with fallback to empty changes."""
        import re

        try:
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return json.loads(match.group())
            return {"changes": {}, "reasoning": "No JSON found in LLM response"}
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse LLM JSON response: {e}")
            return {"changes": {}, "reasoning": f"JSON parse error: {e}"}

    def _get_metrics_from_runner(self) -> dict:
        """Run benchmark and collect metrics."""
        result = self._runner.run()
        return {
            "p50_ms": result.p50_ms,
            "p90_ms": result.p90_ms,
            "p99_ms": result.p99_ms,
            "qps": result.qps,
            "cache_hit_rate": result.cache_hit_rate,
            "gpu_util": result.gpu_util,
        }

    def _build_history_str(self) -> str:
        """Build history string for last 3 rounds."""
        lines = []
        for h in self._history[-3:]:
            lines.append(f"Round {h.round_num}: changed {h.changes} — {h.reasoning}")
        return "\n".join(lines) if lines else "(first round)"

    def tune(self) -> TuningResult:
        """Execute the tuning loop."""
        for iteration in range(self._max_iterations):
            logger.info(f"Tuning round {iteration + 1}/{self._max_iterations}")

            # 1. Measure baseline
            metrics_before = self._get_metrics_from_runner()
            logger.info(f"Metrics before: {metrics_before}")

            # 2. Build prompt and get LLM decision
            history_str = self._build_history_str()
            prompt = ANALYSIS_PROMPT.format(
                p50_ms=metrics_before["p50_ms"],
                p90_ms=metrics_before["p90_ms"],
                p99_ms=metrics_before["p99_ms"],
                qps=metrics_before["qps"],
                cache_hit_rate=metrics_before["cache_hit_rate"],
                gpu_util=metrics_before["gpu_util"],
                config_str=json.dumps(self._config, indent=2),
                batch_size=self._config.get("batch_size", 32),
                chunk_size=self._config.get("chunk_size", 512),
                kv_cache_high_watermark=self._config.get("kv_cache_high_watermark", 0.90),
                prefill_ratio=self._config.get("prefill_ratio", 0.3),
                history=history_str,
            )

            llm_response = self._call_llm(prompt)
            changes = llm_response.get("changes", {})
            logger.info(f"LLM suggested changes: {changes}")

            if not changes:
                logger.info("No changes suggested — assuming converged")
                break

            # 3. Apply changes
            old_config = dict(self._config)
            for param, value in changes.items():
                self._config[param] = value
            try:
                self._tuner.update_config(**changes)
            except Exception as e:
                logger.warning(f"Failed to apply config change: {e}")

            # 4. Measure after changes
            metrics_after = self._get_metrics_from_runner()
            logger.info(f"Metrics after: {metrics_after}")

            # 5. Record history
            self._history.append(
                TuningHistory(
                    round_num=iteration + 1,
                    config=old_config,
                    metrics_before=metrics_before,
                    metrics_after=metrics_after,
                    changes=changes,
                    reasoning=llm_response.get("reasoning", ""),
                )
            )

            # 6. Check convergence — P99 latency improvement
            p99_before = metrics_before["p99_ms"]
            p99_after = metrics_after["p99_ms"]
            if p99_before > 0:
                improvement = (p99_before - p99_after) / p99_before
                logger.info(f"P99 improvement: {improvement:.2%}")
                if improvement < self._threshold and len(self._history) >= 3:
                    recent = self._history[-3:]
                    if all(
                        (h.metrics_before["p99_ms"] - h.metrics_after["p99_ms"])
                        / max(h.metrics_before["p99_ms"], 1)
                        < self._threshold
                        for h in recent
                    ):
                        logger.info("Converged: 3 consecutive rounds below improvement threshold")
                        break

        return TuningResult(
            converged=len(self._history) < self._max_iterations,
            final_config=dict(self._config),
            total_rounds=len(self._history),
            history=list(self._history),
        )
