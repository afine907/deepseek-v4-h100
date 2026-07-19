"""Unit tests for configuration loading."""

import os
import pytest
from src.config.settings import Settings, ModelConfig, BatchingConfig, KVCacheConfig


class TestDefaultConfig:
    def test_model_defaults(self):
        cfg = ModelConfig()
        assert cfg.backend == "mock"
        assert cfg.name == "Qwen/Qwen3.5-0.8B"
        assert cfg.dtype == "bfloat16"
        assert cfg.tensor_parallel_size == 1
        assert cfg.max_num_seqs == 4
        assert cfg.gpu_memory_utilization == 0.50

    def test_batching_defaults(self):
        cfg = BatchingConfig()
        assert cfg.max_batch_size == 32
        assert cfg.prefill_ratio == 0.3
        assert cfg.max_wait_time_ms == 100.0

    def test_kv_cache_defaults(self):
        cfg = KVCacheConfig()
        assert cfg.strategy == "LRU"
        assert cfg.high_watermark == 0.90
        assert cfg.low_watermark == 0.75
        assert cfg.max_evict_per_round == 50


class TestSettingsLoad:
    def test_settings_load_returns_object(self):
        s = Settings.load()
        assert isinstance(s, Settings)
        assert s.model is not None
        assert s.batching is not None
        assert s.kv_cache is not None

    def test_env_override_backend(self):
        os.environ["MODEL_BACKEND"] = "vllm"
        s = Settings.load()
        assert s.model.backend == "vllm"
        del os.environ["MODEL_BACKEND"]
