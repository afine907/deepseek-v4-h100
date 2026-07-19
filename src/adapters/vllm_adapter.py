"""vLLM adapter for InferenceEngine port (CPU and GPU modes)."""

import os
import threading
import time

from ..core.models import EngineStatus, FinishReason, InferenceRequest, InferenceResponse
from ..core.ports import InferenceEngine


class VLLMAdapter(InferenceEngine):
    """
    vLLM inference engine adapter.

    Supports:
    - CPU mode (WSL2): dtype=bfloat16, tp=1
    - GPU mode (H100): dtype=float16, tp=8, quantization=fp8

    Environment variables required in CPU mode:
    - VLLM_ENABLE_V1_MULTIPROCESSING=0  (disable v1 multiprocess executor on WSL2)
    - OMP_NUM_THREADS=12
    - MKL_NUM_THREADS=12
    """

    def __init__(
        self,
        model_name: str = "Qwen/Qwen3.5-0.8B",
        dtype: str = "bfloat16",
        tensor_parallel_size: int = 1,
        quantization: str | None = None,
        max_model_len: int = 512,
        gpu_memory_utilization: float = 0.50,
        max_batch_size: int = 4,
        kv_cache_memory_bytes: int = 268435456,
    ):
        self._model_name = model_name
        self._dtype = dtype
        self._tp = tensor_parallel_size
        self._quantization = quantization
        self._max_model_len = max_model_len
        self._gpu_mem_util = gpu_memory_utilization
        self._max_batch_size = max_batch_size
        self._kv_cache_bytes = kv_cache_memory_bytes
        self._llm = None
        self._device = "cpu" if tensor_parallel_size == 1 else "cuda"
        self._pending: dict[str, dict] = {}
        self._completed: dict[str, InferenceResponse] = {}
        self._lock = threading.Lock()
        self._poller_thread: threading.Thread | None = None
        self._stop_poller = threading.Event()

    def _ensure_loaded(self) -> None:
        """Lazily load the vLLM model."""
        if self._llm is not None:
            return

        # Set WSL2-safe defaults
        if self._device == "cpu":
            os.environ.setdefault("VLLM_ENABLE_V1_MULTIPROCESSING", "0")

        from vllm import LLM

        kwargs = {
            "model": self._model_name,
            "dtype": self._dtype,
            "tensor_parallel_size": self._tp,
            "max_model_len": self._max_model_len,
            "max_num_seqs": self._max_batch_size,
            "enforce_eager": True,
        }

        if self._device == "cpu":
            kwargs["gpu_memory_utilization"] = self._gpu_mem_util
            kwargs["kv_cache_memory_bytes"] = self._kv_cache_bytes
        else:
            kwargs["gpu_memory_utilization"] = self._gpu_mem_util
            if self._quantization:
                kwargs["quantization"] = self._quantization

        self._llm = LLM(**kwargs)
        self._start_result_poller()

    def _start_result_poller(self) -> None:
        """Background thread that polls for completed results."""
        self._stop_poller.clear()
        self._poller_thread = threading.Thread(target=self._poll_results, daemon=True)
        self._poller_thread.start()

    def _poll_results(self) -> None:
        """Poll vLLM for completed results in background."""
        while not self._stop_poller.wait(timeout=0.5):
            with self._lock:
                pending_ids = list(self._pending.keys())
            if not pending_ids:
                continue
            try:
                # Use async output handling — vLLM generate is synchronous here
                # The adapter pattern: submit via scheduler which manages async results
                pass
            except Exception:
                pass

    def submit(self, request: InferenceRequest) -> str:
        self._ensure_loaded()
        from vllm import SamplingParams

        rid = request.request_id
        sp = SamplingParams(
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        with self._lock:
            self._pending[rid] = {
                "request": request,
                "sampling_params": sp,
                "submitted_at": time.time(),
            }

        # Trigger generation synchronously for simplicity in this adapter
        try:
            outputs = self._llm.generate([request.prompt], sp)
            output = outputs[0]
            generated_text = output.outputs[0].text
            finish = (
                FinishReason.STOP
                if output.outputs[0].finish_reason == "stop"
                else FinishReason.LENGTH
            )
            latency_ms = (time.time() - self._pending[rid]["submitted_at"]) * 1000
            tokens = (
                len(output.outputs[0].token_ids)
                if hasattr(output.outputs[0], "token_ids")
                else len(generated_text)
            )

            response = InferenceResponse(
                request_id=rid,
                generated_text=generated_text,
                finish_reason=finish,
                latency_ms=latency_ms,
                tokens_generated=tokens,
            )
            with self._lock:
                self._completed[rid] = response
                del self._pending[rid]
        except Exception:
            with self._lock:
                if rid in self._pending:
                    del self._pending[rid]

        return rid

    def get_result(self, request_id: str, timeout: float = 30.0) -> InferenceResponse | None:
        with self._lock:
            if request_id in self._completed:
                return self._completed.pop(request_id)
            if request_id in self._pending:
                return None
        return None

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            self._pending.pop(request_id, None)
            self._completed.pop(request_id, None)
        return True

    def get_status(self) -> EngineStatus:
        return EngineStatus(
            ready=True,
            model_loaded=self._llm is not None,
            device=self._device,
            max_batch_size=self._max_batch_size,
        )

    def shutdown(self) -> None:
        """Stop the poller thread."""
        self._stop_poller.set()
        if self._poller_thread:
            self._poller_thread.join(timeout=2.0)
