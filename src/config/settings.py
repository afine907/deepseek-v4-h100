"""Configuration loader with environment variable overrides."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).parent.parent.parent / "configs"


@dataclass
class ModelConfig:
    backend: str = "mock"
    name: str = "Qwen/Qwen3.5-0.8B"
    tensor_parallel_size: int = 1
    dtype: str = "bfloat16"
    max_model_len: int = 512
    max_num_seqs: int = 4
    gpu_memory_utilization: float = 0.50
    kv_cache_memory_bytes: int = 268435456
    quantization: str | None = None


@dataclass
class BatchingConfig:
    max_batch_size: int = 32
    prefill_ratio: float = 0.3
    max_wait_time_ms: float = 100.0


@dataclass
class KVCacheConfig:
    strategy: str = "LRU"
    high_watermark: float = 0.90
    low_watermark: float = 0.75
    max_evict_per_round: int = 50


@dataclass
class AgentConfig:
    llm_provider: str = "mock"
    api_key_env: str = "ANTHROPIC_API_KEY"
    model_name: str = "claude-sonnet-4-20250514"
    max_iterations: int = 10
    convergence_threshold: float = 0.05


@dataclass
class Settings:
    model: ModelConfig = field(default_factory=ModelConfig)
    batching: BatchingConfig = field(default_factory=BatchingConfig)
    kv_cache: KVCacheConfig = field(default_factory=KVCacheConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)

    @classmethod
    def load(cls) -> "Settings":
        def _load_yaml(name: str):
            path = CONFIG_DIR / f"{name}.yaml"
            if path.exists():
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                    # Flatten nested config (e.g., "model:" section)
                    if name in data:
                        return data[name]
                    return data
            return {}

        s = cls()

        # Load model config
        model_data = _load_yaml("model")
        if model_data:
            for key, value in model_data.items():
                if hasattr(s.model, key):
                    setattr(s.model, key, value)

        # Load batching config
        batching_data = _load_yaml("batching")
        if batching_data:
            for key, value in batching_data.items():
                if hasattr(s.batching, key):
                    setattr(s.batching, key, value)

        # Load KV cache config
        kv_data = _load_yaml("kv_cache")
        if kv_data:
            for key, value in kv_data.items():
                if key == "eviction_policy":
                    key = "strategy"
                if hasattr(s.kv_cache, key):
                    setattr(s.kv_cache, key, value)

        # Load agent config
        agent_data = _load_yaml("agent")
        if agent_data:
            for key, value in agent_data.items():
                if hasattr(s.agent, key):
                    setattr(s.agent, key, value)

        # Environment variable overrides
        if os.getenv("MODEL_BACKEND"):
            s.model.backend = os.getenv("MODEL_BACKEND")
        if os.getenv("MODEL_NAME"):
            s.model.name = os.getenv("MODEL_NAME")
        if os.getenv("VLLM_ENABLE_V1_MULTIPROCESSING") is None:
            os.environ["VLLM_ENABLE_V1_MULTIPROCESSING"] = "0"

        return s


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings
