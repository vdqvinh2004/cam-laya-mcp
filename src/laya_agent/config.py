from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

HOME = Path.home()
CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "laya-agent"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", HOME / ".local/state")) / "laya-agent"
CONFIG_FILE = CONFIG_DIR / "config.toml"


@dataclass(frozen=True)
class Config:
    enabled: bool = False
    model: str = "aac6fef/laya-mlx"
    confidence_threshold: float = 0.55
    mandatory_safety: bool = False
    cache_ttl_seconds: int = 300
    preload: bool = False


def load_config(path: Path = CONFIG_FILE) -> Config:
    try:
        raw = tomllib.loads(path.read_text())
    except FileNotFoundError:
        return Config()
    values = {k: v for k, v in raw.items() if k in Config.__dataclass_fields__}
    for key in ("enabled", "mandatory_safety", "preload"):
        if key in values and type(values[key]) is not bool:
            raise ValueError(f"{key} must be a boolean")
    if "model" in values and (not isinstance(values["model"], str) or not values["model"]):
        raise ValueError("model must be a nonempty string")
    if "cache_ttl_seconds" in values and (type(values["cache_ttl_seconds"]) is not int or values["cache_ttl_seconds"] < 0):
        raise ValueError("cache_ttl_seconds must be a nonnegative integer")
    if "confidence_threshold" in values and type(values["confidence_threshold"]) not in {int, float}:
        raise ValueError("confidence_threshold must be a number")
    config = Config(**values)
    if not 0 <= config.confidence_threshold <= 1 or config.cache_ttl_seconds < 0:
        raise ValueError("Invalid laya-agent configuration")
    return config


def write_default(path: Path = CONFIG_FILE) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('enabled = false\nmodel = "aac6fef/laya-mlx"\nconfidence_threshold = 0.55\nmandatory_safety = false\ncache_ttl_seconds = 300\npreload = false\n')
    path.chmod(0o600)
