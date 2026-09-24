from __future__ import annotations

import fcntl
import json
import os
import re
import socket
import socketserver
import subprocess
import sys
import threading
import time
import uuid

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
                queued = time.perf_counter()
                with self.server.metrics_lock:
                    queue_ms = round((time.perf_counter() - queued) * 1000, 2)
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
                    trace = self.server.engine.last_trace
                    with events.open("a") as log:
                        log.write(json.dumps({
                            "time": round(time.time()), "invocation_id": req.get("invocation_id"),
                            "run_id": req.get("run_id"), "source": source, "policy": req["policy"],
                            "decision": out.get("decision", out.get("risk")), "confidence": out.get("confidence"),
                            "queue_ms": queue_ms, **trace,
                            "success": out.get("reason_code") != "runtime_unavailable",
                        }) + "\n")
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
    run_id = os.environ.get("CAM_LAYA_RUN_ID", "")
    run_id = run_id if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", run_id) else None
    invocation_id = uuid.uuid4().hex
    payload = (json.dumps({"op": op, "policy": policy, "state": state or {}, "source": source, "invocation_id": invocation_id, "run_id": run_id}, separators=(",", ":")) + "\n").encode()
    if len(payload) > 8192:
        raise ValueError("request too large")
    started = time.perf_counter()

    def record(status: str, connected: float | None = None) -> None:
        if not run_id or op != "decide":
            return
        path = STATE_DIR / "client-events.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if path.exists() and path.stat().st_size > 1_000_000:
            path.replace(path.with_suffix(".jsonl.1"))
        with path.open("a") as log:
            log.write(json.dumps({
                "run_id": run_id, "invocation_id": invocation_id, "source": source, "policy": policy,
                "status": status, "connect_ms": round(((connected or time.perf_counter()) - started) * 1000, 2),
                "transport_ms": round((time.perf_counter() - connected) * 1000, 2) if connected else None,
                "total_ms": round((time.perf_counter() - started) * 1000, 2),
            }) + "\n")
        path.chmod(0o600)

    for attempt in range(20 if start else 1):
        with socket.socket(socket.AF_UNIX) as sock:
            sock.settimeout(timeout)
            try:
                sock.connect(str(SOCKET))
            except OSError:
                if attempt == 0 and start:
                    STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
                    subprocess.Popen([sys.executable, "-m", "laya_agent.daemon"], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                time.sleep(0.05)
                continue
            connected = time.perf_counter()
            try:
                sock.sendall(payload)
                response = b""
                while not response.endswith(b"\n") and len(response) <= 8192:
                    chunk = sock.recv(8192)
                    if not chunk:
                        break
                    response += chunk
                result = json.loads(response)
            except OSError as exc:
                record("timeout" if isinstance(exc, TimeoutError) else "failure", connected)
                raise
            except ValueError:
                record("failure", connected)
                raise
            record("completed", connected)
            return result
    record("connection_failure")
    raise ConnectionError("local Laya process unavailable")


if __name__ == "__main__":
    serve()
