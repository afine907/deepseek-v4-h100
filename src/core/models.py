"""Data models for DeepSeek-V4-Flash inference system."""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TIMEOUT = "timeout"


@dataclass
class InferenceRequest:
    """Inference request from a client."""

    request_id: str
    prompt: str
    max_tokens: int = 256
    temperature: float = 0.7
    metadata: dict = field(default_factory=dict)


@dataclass
class InferenceResponse:
    """Inference response returned to a client."""

    request_id: str
    generated_text: str
    finish_reason: FinishReason
    latency_ms: float
    tokens_generated: int


@dataclass
class EngineStatus:
    """Current status of the inference engine."""

    ready: bool
    model_loaded: bool
    device: str  # "cpu" or "cuda:0"
    max_batch_size: int


@dataclass
class QueueStatus:
    """Current status of the scheduler queue."""

    waiting_requests: int
    running_requests: int
    avg_wait_time_ms: float
    avg_decode_time_ms: float


@dataclass
class ChunkedPrefillConfig:
    """Configuration for chunked prefill."""

    chunk_size: int = 512
    max_chunks_per_request: int = 64
    prefill_ratio: float = 0.3


@dataclass
class BatchConfig:
    """Configuration for continuous batching."""

    max_batch_size: int = 32
    prefill_ratio: float = 0.3
    max_wait_time_ms: float = 100.0


@dataclass
class KVCacheConfig:
    """Configuration for KV cache management."""

    strategy: str = "LRU"
    high_watermark: float = 0.90
    low_watermark: float = 0.75
    max_evict_per_round: int = 50
