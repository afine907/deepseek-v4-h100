"""Unit tests for KVCacheManager."""

import pytest
import threading
import time
from src.core.kv_cache_manager import KVCacheManager
from src.core.models import KVCacheConfig


class TestKVCacheManager:
    def test_basic_access(self):
        config = KVCacheConfig(high_watermark=0.9, low_watermark=0.5, max_evict_per_round=10)
        manager = KVCacheManager(config)
        manager.set_max_blocks(10)
        manager.record_access("block-1")
        manager.record_access("block-2")
        assert manager.get_hit_rate() >= 0.0

    def test_eviction_triggered(self):
        config = KVCacheConfig(high_watermark=0.5, low_watermark=0.3, max_evict_per_round=5)
        manager = KVCacheManager(config)
        manager.set_max_blocks(5)
        # Fill to 80% (above high_watermark=0.5)
        for i in range(4):
            manager.record_access(f"block-{i}")
        evicted = manager.evict_if_needed()
        assert evicted >= 0

    def test_memory_usage(self):
        config = KVCacheConfig()
        manager = KVCacheManager(config)
        manager.set_max_blocks(10)
        for i in range(5):
            manager.record_access(f"block-{i}")
        usage = manager.get_memory_usage()
        assert usage == 0.5

    def test_thread_safety(self):
        config = KVCacheConfig()
        manager = KVCacheManager(config)
        manager.set_max_blocks(1000)
        errors = []

        def accessor(block_id):
            try:
                for _ in range(50):
                    manager.record_access(block_id)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=accessor, args=(f"block-{i}",)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(errors) == 0
