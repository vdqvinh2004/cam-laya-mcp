from __future__ import annotations

import importlib.metadata
import platform
import sys
import threading
import time

from .config import Config


def environment() -> dict:
    mac = platform.mac_ver()[0]
    supported = sys.platform == "darwin" and platform.machine() == "arm64" and sys.version_info >= (3, 11) and bool(mac) and tuple(int(x) for x in mac.split(".")[:1]) >= (14,)
    try:
        version = importlib.metadata.version("laya-mlx")
    except importlib.metadata.PackageNotFoundError:
        version = None
    return {"platform": f"{sys.platform}-{platform.machine()}", "macos": mac, "python": platform.python_version(), "supported": supported, "installed": version is not None, "version": version}


class Runtime:
    def __init__(self, config: Config):
        self.config = config
        self._agent = None
        self._lock = threading.RLock()
        self.load_ms = None
        self.last_load_ms = None
        self.last_inference_ms = None

    @property
    def loaded(self) -> bool:
        return self._agent is not None

    def load(self):
        if not environment()["supported"]:
            raise RuntimeError("Laya-MLX requires Apple Silicon, macOS 14+, Python 3.11+")
        with self._lock:
            if self._agent is None:
                import laya_mlx
                start = time.perf_counter()
                try:
                    self._agent = laya_mlx.load(self.config.model, dtype="float16")
                finally:
                    self.load_ms = self.last_load_ms = round((time.perf_counter() - start) * 1000, 2)
            return self._agent

    def predict(self, state: dict, question: dict) -> dict:
        with self._lock:
            agent = self.load()
            start = time.perf_counter()
            try:
                answer = agent.predict(state, {"decision": question})
            finally:
                self.last_inference_ms = round((time.perf_counter() - start) * 1000, 2)
        return answer["answers"]["decision"]
