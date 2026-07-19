"""Tuner interface (abstract + REST client implementation)."""

from abc import ABC, abstractmethod
from typing import Any


class TunerInterface(ABC):
    """Abstract interface for the tuning control plane."""

    @abstractmethod
    def update_config(self, **kwargs: Any) -> dict:
        """Update configuration. Returns actual applied config."""
        ...

    @abstractmethod
    def get_status(self) -> dict:
        """Get current system status."""
        ...

    @abstractmethod
    def get_metrics(self) -> dict:
        """Get current metrics."""
        ...


class RESTTuner(TunerInterface):
    """REST client implementation of TunerInterface."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self._base_url = base_url.rstrip("/")

    def update_config(self, **kwargs: Any) -> dict:
        import requests
        resp = requests.post(f"{self._base_url}/config", json=kwargs, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_status(self) -> dict:
        import requests
        resp = requests.get(f"{self._base_url}/status", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def get_metrics(self) -> dict:
        import requests
        resp = requests.get(f"{self._base_url}/metrics", timeout=10)
        resp.raise_for_status()
        return resp.json()
