from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
from functools import lru_cache
from pathlib import Path

KEYS = frozenset({"task_type", "current_phase", "language", "framework", "git_dirty", "changed_files", "tests_available", "last_test_result", "test_status", "risk", "last_action", "last_result", "scope", "client"})
SECRET = re.compile(r"(?i)(token|secret|password|credential|api.?key|authorization)")


def compact(value: dict, *, max_bytes: int = 2048) -> dict:
    """Whitelist compact facts and reject secrets and oversized model input."""
    if not isinstance(value, dict):
        raise ValueError("state must be an object")
    result = {}
    for key in sorted(KEYS & value.keys()):
        item = value[key]
        if SECRET.search(key) or isinstance(item, (dict, list)):
            continue
        if isinstance(item, (str, bool, int, float)) and (not isinstance(item, float) or math.isfinite(item)) and not SECRET.search(str(item)):
            result[key] = item[:160] if isinstance(item, str) else item
    if len(json.dumps(result).encode()) > max_bytes:
        raise ValueError("state too large")
    return result


def fingerprint(*parts: object) -> str:
    return hashlib.sha256(json.dumps(parts, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def git_facts(cwd: Path | None = None) -> dict:
    try:
        result = subprocess.run(["git", "-c", "core.quotepath=false", "status", "--porcelain", "-z"], cwd=cwd, capture_output=True, text=True, timeout=2, check=True)
        lines = [part for part in result.stdout.split("\0") if len(part) >= 4 and part[2] == " " and set(part[:2]) <= set(" MADRCU?!")]
        root = cwd or Path.cwd()
        revision = []
        for line in lines:
            file = root / line[3:]
            try:
                stat = file.stat()
                revision.append((line, stat.st_mtime_ns, stat.st_size))
            except OSError:
                revision.append((line,))
        return {"git_dirty": bool(lines), "changed_files": len(lines), "cache_revision": fingerprint(result.stdout, revision)}
    except (OSError, subprocess.SubprocessError):
        return {}


@lru_cache(maxsize=128)
def _project_manifest(path: str, signature: tuple[int, int, bool]) -> dict:
    file = Path(path)
    if file.name == "package.json":
        try:
            data = json.loads(file.read_text())
            deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
            framework = next((name for name in ("next", "react", "vue") if name in deps), None)
            return {"language": "typescript" if (file.parent / "tsconfig.json").exists() else "javascript", "framework": "nextjs" if framework == "next" else framework, "tests_available": "test" in data.get("scripts", {})}
        except (OSError, ValueError, TypeError):
            return {}
    if file.name == "pyproject.toml":
        return {"language": "python", "tests_available": (file.parent / "tests").exists()}
    if file.name == "Cargo.toml":
        return {"language": "rust", "tests_available": (file.parent / "tests").exists()}
    return {}


def project_facts(cwd: Path | None = None) -> dict:
    root = cwd or Path.cwd()
    for name in ("package.json", "pyproject.toml", "Cargo.toml"):
        file = root / name
        try:
            tsconfig = root / "tsconfig.json"
            signature = (file.stat().st_mtime_ns, tsconfig.stat().st_mtime_ns if tsconfig.exists() else 0, (root / "tests").exists())
            return _project_manifest(str(file), signature)
        except FileNotFoundError:
            continue
    return {}
