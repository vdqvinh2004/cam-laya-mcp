from __future__ import annotations

import fcntl
import json
import os
import socket
import socketserver
import subprocess
import sys
import threading
import time

from .config import CONFIG_FILE, STATE_DIR, load_config
from .policy import OPTIONS, DecisionEngine

SOCKET = STATE_DIR / "agent.sock"
METRICS = STATE_DIR / "stats.json"
PIDFILE = STATE_DIR / "agent.pid"


class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.server.last_activity = time.monotonic()
        modified = CONFIG_FILE.stat().st_mtime_ns if CONFIG_FILE.exists() else 0
        if modified != self.server.config_mtime:
            with self.server.config_lock:
                if modified != self.server.config_mtime:
                    with self.server.metrics_lock:
                        replacement = DecisionEngine(load_config())
                        replacement.counts.update(self.server.engine.counts)
                        self.server.engine = replacement
                        self.server.config_mtime = modified
        try:
            raw = self.rfile.readline(8193)
            if len(raw) > 8192:
                raise ValueError("request too large")
            req = json.loads(raw)
            if req.get("op") == "status":
                out = self.server.engine.status()
            elif req.get("op") == "stats":
                out = self.server.engine.stats()
            elif req.get("op") == "decide":
                # ponytail: one lock keeps cache and counters consistent; split it if decision throughput matters.
                with self.server.metrics_lock:
                    source = req.get("source")
                    if source in {"mcp", "hook"}:
                        self.server.engine.counts[f"{source}_decisions"] += 1
                    out = self.server.engine.decide(req["policy"], req.get("state", {}))
                    tmp = METRICS.with_suffix(".tmp")
                    tmp.write_text(json.dumps(self.server.engine.stats()))
                    tmp.replace(METRICS)
                    events = STATE_DIR / "events.jsonl"
                    if events.exists() and events.stat().st_size > 1_000_000:
                        events.replace(events.with_suffix(".jsonl.1"))
                    with events.open("a") as log:
                        log.write(json.dumps({"time": round(time.time()), "policy": req["policy"], "decision": out.get("decision", out.get("risk")), "confidence": out.get("confidence"), "latency_ms": self.server.engine.latencies[-1] if self.server.engine.latencies else None, "success": out.get("reason_code") != "runtime_unavailable"}) + "\n")
                    os.chmod(events, 0o600)
            elif req.get("op") == "preload":
                self.server.engine.runtime.load()
                out = self.server.engine.status()
            elif req.get("op") == "task_changed":
                self.server.engine.cache.clear()
                out = {"cache_cleared": True}
            elif req.get("op") == "shutdown":
                self.server.running = False
                out = {"stopped": True}
            else:
                raise ValueError("invalid operation")
        except Exception as exc:
            out = {"error": type(exc).__name__}
        self.wfile.write((json.dumps(out, separators=(",", ":")) + "\n").encode())


class LocalServer(socketserver.ThreadingUnixStreamServer):
    daemon_threads = True


def serve() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE_DIR.chmod(0o700)
    lock = (STATE_DIR / "agent.lock").open("w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return
    if SOCKET.exists():
        try:
            with socket.socket(socket.AF_UNIX) as probe:
                probe.settimeout(0.2)
                probe.connect(str(SOCKET))
            return
        except OSError:
            SOCKET.unlink()
    with LocalServer(str(SOCKET), Handler) as server:
        os.chmod(SOCKET, 0o600)
        server.engine = DecisionEngine(load_config())
        try:
            saved = json.loads(METRICS.read_text())
            if not isinstance(saved, dict):
                raise ValueError("invalid saved stats")
            for key in ("laya_decisions", "cache_hits", "laya_failures", "hard_rules", "escalations", "estimated_llm_calls_avoided", "estimated_tokens_saved", "mcp_decisions", "hook_decisions"):
                server.engine.counts[key] = int(saved.get(key, 0))
            by_policy = saved.get("decisions_by_policy", {})
            if not isinstance(by_policy, dict):
                raise ValueError("invalid saved policy stats")
            for policy in OPTIONS:
                server.engine.counts[f"policy_{policy}"] = int(by_policy.get(policy, 0))
        except (FileNotFoundError, ValueError, TypeError):
            pass
        server.metrics_lock = threading.Lock()
        server.config_lock = threading.Lock()
        server.config_mtime = CONFIG_FILE.stat().st_mtime_ns if CONFIG_FILE.exists() else 0
        server.running = True
        server.last_activity = time.monotonic()
        server.timeout = 60
        PIDFILE.write_text(str(os.getpid()))
        PIDFILE.chmod(0o600)
        try:
            while server.running and time.monotonic() - server.last_activity < 1800:
                server.handle_request()
        finally:
            SOCKET.unlink(missing_ok=True)
            PIDFILE.unlink(missing_ok=True)


def request(op: str, *, policy: str | None = None, state: dict | None = None, source: str | None = None, start: bool = True, timeout: float = 10) -> dict:
    payload = (json.dumps({"op": op, "policy": policy, "state": state or {}, "source": source}, separators=(",", ":")) + "\n").encode()
    if len(payload) > 8192:
        raise ValueError("request too large")
    for attempt in range(20 if start else 1):
        try:
            with socket.socket(socket.AF_UNIX) as sock:
                sock.settimeout(timeout)
                sock.connect(str(SOCKET))
                sock.sendall(payload)
                response = b""
                while not response.endswith(b"\n") and len(response) <= 8192:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break
                    response += chunk
                return json.loads(response)
        except (OSError, ValueError):
            if attempt == 0 and start:
                STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
                subprocess.Popen([sys.executable, "-m", "laya_agent.daemon"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            time.sleep(0.05)
    raise ConnectionError("local Laya process unavailable")


if __name__ == "__main__":
    serve()
