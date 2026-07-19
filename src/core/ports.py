"""Port interfaces (hexagonal architecture inbound ports)."""

from abc import ABC, abstractmethod

from .models import EngineStatus, InferenceRequest, InferenceResponse, QueueStatus


class InferenceEngine(ABC):
    """Inbound port for inference engine operations."""

    @abstractmethod
    def submit(self, request: InferenceRequest) -> str:
        """Submit an inference request, returning request_id."""
        ...

    @abstractmethod
    def get_result(self, request_id: str, timeout: float = 30.0) -> InferenceResponse | None:
        """Get inference result (non-blocking). Returns None if not yet complete."""
        ...

    @abstractmethod
    def cancel(self, request_id: str) -> bool:
        """Cancel a running request."""
        ...

    @abstractmethod
    def get_status(self) -> EngineStatus:
        """Get engine status."""
        ...


class SchedulerPort(ABC):
    """Inbound port for request scheduling."""

    @abstractmethod
    def enqueue(self, request: InferenceRequest) -> str:
        """Enqueue a request, returning request_id."""
        ...

    @abstractmethod
    def step(self) -> list[InferenceResponse]:
        """Execute one scheduling step. Returns list of completed responses this round."""
        ...

    @abstractmethod
    def get_queue_status(self) -> QueueStatus:
        """Get current queue status."""
        ...


class KVCacheManagerPort(ABC):
    """Inbound port for KV cache management."""

    @abstractmethod
    def evict_if_needed(self) -> int:
        """Trigger eviction if needed. Returns number of blocks evicted."""
        ...

    @abstractmethod
    def record_access(self, block_id: str) -> None:
        """Record that a block was accessed."""
        ...

    @abstractmethod
    def get_hit_rate(self) -> float:
        """Get cache hit rate."""
        ...


class MetricsCollectorPort(ABC):
    """Inbound port for metrics collection."""

    @abstractmethod
    def record_latency(self, latency_ms: float, stage: str = "inference") -> None:
        """Record inference latency."""
        ...

    @abstractmethod
    def record_throughput(self, tokens: int) -> None:
        """Record tokens generated."""
        ...

    @abstractmethod
    def get_metrics(self) -> dict:
        """Get all current metrics."""
        ...
