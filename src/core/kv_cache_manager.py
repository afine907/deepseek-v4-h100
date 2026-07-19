"""Block-level LRU KV Cache manager."""

import threading
import time
from collections import OrderedDict

from .models import KVCacheConfig
from .ports import KVCacheManagerPort


class Block:
    """Represents one KV cache block."""

    def __init__(self, block_id: str):
        self.block_id = block_id
        self.last_access = time.time()
        self.size_mb: float = 0.0


class KVCacheManager(KVCacheManagerPort):
    """
    Block-level LRU KV Cache manager.

    Eviction policy: when usage exceeds high_watermark, evict blocks
    until usage drops to low_watermark (at most max_evict_per_round).
    Thread-safe: all operations are protected by self._lock.
    """

    def __init__(self, config: KVCacheConfig):
        self._config = config
        self._blocks: OrderedDict[str, Block] = OrderedDict()
        self._max_blocks = 1000
        self._hit_count = 0
        self._miss_count = 0
        self._eviction_count = 0
        self._lock = threading.Lock()

    def set_max_blocks(self, max_blocks: int) -> None:
        """Set max blocks based on available GPU memory. Thread-safe."""
        with self._lock:
            self._max_blocks = max_blocks

    def _evict_locked(self) -> int:
        """
        Perform eviction. Caller must hold self._lock.
        Returns number of blocks evicted.
        """
        current_len = len(self._blocks)
        if self._max_blocks <= 0:
            return 0
        usage = current_len / self._max_blocks
        if usage < self._config.high_watermark:
            return 0

        evicted = 0
        target = int(self._max_blocks * self._config.low_watermark)
        while (
            len(self._blocks) > target
            and len(self._blocks) > 0
            and evicted < self._config.max_evict_per_round
        ):
            self._blocks.popitem(last=False)
            self._eviction_count += 1
            evicted += 1
        return evicted

    def evict_if_needed(self) -> int:
        """Evict blocks if above high watermark. Returns evicted count."""
        with self._lock:
            return self._evict_locked()

    def record_access(self, block_id: str) -> None:
        """Record a block access (moves to end of LRU order)."""
        with self._lock:
            if block_id in self._blocks:
                self._blocks.move_to_end(block_id)
                self._blocks[block_id].last_access = time.time()
                self._hit_count += 1
            else:
                self._blocks[block_id] = Block(block_id)
                self._miss_count += 1
                self._evict_locked()  # Already holding lock — no deadlock

    def get_hit_rate(self) -> float:
        """Return cache hit rate."""
        with self._lock:
            total = self._hit_count + self._miss_count
            return self._hit_count / total if total > 0 else 0.0

    def get_eviction_count(self) -> int:
        with self._lock:
            return self._eviction_count

    def get_memory_usage(self) -> float:
        """Return current memory usage ratio (0.0 to 1.0)."""
        with self._lock:
            if self._max_blocks <= 0:
                return 0.0
            return len(self._blocks) / self._max_blocks
