from __future__ import annotations

import argparse
import asyncio
import importlib.metadata
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from .config import CONFIG_FILE, STATE_DIR, load_config, write_default
from .daemon import SOCKET, request
from .hooks import run as run_hook
from .integrations import ADAPTERS
from .runtime import environment

ISOLATED_VENV = Path.home() / ".local/share/laya-agent/venv"


def _isolated_exe() -> Path | None:
    executable = ISOLATED_VENV / "bin/cam-laya-mcp"
    if not executable.exists():
        executable = ISOLATED_VENV / "bin/laya-agent"
    if (ISOLATED_VENV / ".laya-agent-owned").exists() and executable.exists():
        return executable
    return None


def _json(data: dict) -> None:
    print(json.dumps(data, indent=2))


def _exe() -> str:
    return shutil.which("cam-laya-mcp") or shutil.which("laya-agent") or str(Path(sys.executable).parent / "cam-laya-mcp")


def setup(args) -> int:
    env = environment()
    _json(env)
    if not env["supported"]:
        print("Unsupported: Laya-MLX requires Apple Silicon, macOS 14+, Python 3.11+. Agent integrations were not changed.")
        return 1
    isolated = _isolated_exe()
    if isolated and subprocess.run([str(ISOLATED_VENV / "bin/python"), "-c", "import laya_mlx"], capture_output=True).returncode:
        isolated = None
    executable = str(isolated) if isolated else _exe()
    smoke_ok = False
    if env["installed"] and not isolated:
        try:
            smoke_ok = subprocess.run([executable, "test"], capture_output=True, timeout=60).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not isolated and not smoke_ok:
        if (ISOLATED_VENV / ".laya-agent-owned").exists() or args.yes:
            approved = True
        elif sys.stdin.isatty():
            approved = input("Laya-MLX is unavailable to cam-laya-mcp. Install an isolated local runtime now? [Y/n] ").strip().lower() in {"", "y", "yes"}
        else:
            print("Laya-MLX missing. Run interactively or pass --yes to approve installation.")
            return 1
        if not approved:
            print("Installation declined. Existing coding agents continue normally.")
            return 0
        if not shutil.which("uv"):
            print("uv is required to create the isolated runtime: https://docs.astral.sh/uv/")
            return 1
        venv = ISOLATED_VENV
        if venv.exists() and not (venv / ".laya-agent-owned").exists():
            print(f"Existing unowned environment at {venv}; move it before setup.")
            return 1
        if not (venv / "bin/python").exists():
            subprocess.run(["uv", "venv", "--python", "3.12", str(venv)], check=True)
        source = Path(__file__).resolve().parents[2]
        package = str(source) + "[mlx]" if (source / "pyproject.toml").exists() else "cam-laya-mcp[mlx]"
        subprocess.run(["uv", "pip", "install", "--python", str(venv / "bin/python"), package], check=True)
        (venv / ".laya-agent-owned").touch()
        executable = str(venv / "bin/cam-laya-mcp")
        subprocess.run([str(venv / "bin/python"), "-c", "import laya_mlx; print('Laya-MLX import: OK')"], check=True)
    elif isolated:
        executable = str(isolated)
    write_default()
    # Loading performs checkpoint discovery/download via current Laya-MLX API.
    if not smoke_ok and subprocess.run([executable, "test"], text=True).returncode:
        print("Model smoke test failed; agent configuration was not changed.")
        return 1
    failed = False
    for adapter in ADAPTERS:
        if adapter.detect():
            try:
                adapter.install(executable)
                result = adapter.validate()
                print(f"{adapter.name}: {result}")
                failed |= not result["installed"]
            except Exception as exc:
                print(f"{adapter.name}: setup failed ({type(exc).__name__}: {exc})")
                failed = True
    return 1 if failed else 0


def doctor() -> dict:
    env = environment()
    isolated = _isolated_exe()
    env["isolated_runtime"] = bool(isolated)
    if isolated:
        info = subprocess.run([str(ISOLATED_VENV / "bin/python"), "-c", "import importlib.metadata,json,platform; print(json.dumps({'python':platform.python_version(),'laya':importlib.metadata.version('laya-mlx'),'mlx':importlib.metadata.version('mlx')}))"], capture_output=True, text=True, timeout=10)
        if info.returncode == 0:
            env["runtime_versions"] = json.loads(info.stdout)
            env["installed"] = True
            env["version"] = env["runtime_versions"]["laya"]
    try:
        model = load_config().model
        env["config_error"] = None
    except Exception as exc:
        model = "aac6fef/laya-mlx"
        env["config_error"] = type(exc).__name__
    hub = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"))
    cache_path = Path(model) if Path(model).exists() else hub / ("models--" + model.replace("/", "--"))
    try:
        process = request("status", start=False, timeout=1)
    except Exception:
        process = None
    from .daemon import PIDFILE
    env.update({"uv": bool(shutil.which("uv")), "config": CONFIG_FILE.exists(), "model_cache": cache_path.exists(), "process": process, "pid": PIDFILE.read_text().strip() if PIDFILE.exists() else None, "socket": SOCKET.exists(), "executable_on_path": bool(shutil.which("cam-laya-mcp") or shutil.which("laya-agent")), "state_dir_private": not STATE_DIR.exists() or STATE_DIR.stat().st_mode & 0o077 == 0})
    env["mcp"] = importlib.util.find_spec("mcp") is not None
    env["mlx"] = importlib.util.find_spec("mlx") is not None or "runtime_versions" in env
    if env["mlx"]:
        env["mlx_version"] = env["runtime_versions"]["mlx"] if "runtime_versions" in env else importlib.metadata.version("mlx")
    clients = {}
    for adapter in ADAPTERS:
        try:
            clients[adapter.name] = {"detected": adapter.detect(), **adapter.validate()}
        except Exception as exc:
            clients[adapter.name] = {"detected": adapter.detect(), "config_error": type(exc).__name__}
    env["clients"] = clients
    return env


def benchmark() -> dict:
    from .context import compact
    from .hooks import run as hook_run
    from .policy import DecisionEngine
    engine = DecisionEngine(load_config())
    cold = time.perf_counter()
    subprocess.run([sys.executable, "-c", "import laya_agent"], capture_output=True, timeout=10)
    cold_start_ms = round((time.perf_counter() - cold) * 1000, 2)
    start = time.perf_counter()
    try:
        engine.runtime.load()
        load_ms = round((time.perf_counter() - start) * 1000, 2)
        state = {"current_phase": "testing", "language": "python", "tests_available": True}
        samples = []
        for _ in range(5):
            t = time.perf_counter()
            engine.runtime.predict(state, {"type": "choice", "instructions": "Choose next step", "criteria": ["test", "review"]})
            samples.append(round((time.perf_counter() - t) * 1000, 2))
        t = time.perf_counter()
        engine.decide("test_decision", state)
        engine.decide("test_decision", state)
        cache_ms = round((time.perf_counter() - t) * 1000, 2)
        t = time.perf_counter()
        compact(state)
        context_ms = round((time.perf_counter() - t) * 1000, 2)
        t = time.perf_counter()
        hook_run("codex", "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "git status"}})
        hook_ms = round((time.perf_counter() - t) * 1000, 2)
        t = time.perf_counter()
        engine.decide("risk_check", {"action": "git push origin main"})
        risk_ms = round((time.perf_counter() - t) * 1000, 2)
        t = time.perf_counter()
        engine.decide("route_task", {"request": "Fix the checkout bug"})
        route_ms = round((time.perf_counter() - t) * 1000, 2)

        async def roundtrip():
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            server = StdioServerParameters(command=sys.executable, args=["-m", "laya_agent.mcp_server"])
            async with stdio_client(server) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    start_call = time.perf_counter()
                    await session.call_tool("laya_status", {})
                    return round((time.perf_counter() - start_call) * 1000, 2)

        mcp_ms = asyncio.run(roundtrip())
        return {"environment": environment(), "cold_start_ms": cold_start_ms, "model_load_ms": load_ms, "warm_decision_ms": samples, "risk_decision_ms": risk_ms, "task_route_ms": route_ms, "mcp_roundtrip_ms": mcp_ms, "hook_overhead_ms": hook_ms, "context_serialization_ms": context_ms, "repeated_decision_ms": cache_ms, "cache_hit_percent": round(100 * engine.counts["cache_hits"] / max(engine.counts["requests"], 1), 1)}
    except Exception as exc:
        return {"error": type(exc).__name__, "environment": environment()}


def main() -> None:
    parser = argparse.ArgumentParser(prog="cam-laya-mcp")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("setup").add_argument("--yes", action="store_true")
    for name in ("status", "doctor", "benchmark", "stats", "test", "enable", "disable", "configure", "mcp"):
        sub.add_parser(name)
    uninstall = sub.add_parser("uninstall")
    uninstall.add_argument("--remove-runtime", action="store_true")
    uninstall.add_argument("--remove-model-cache", action="store_true")
    uninstall.add_argument("--remove-config", action="store_true")
    hook = sub.add_parser("hook")
    hook.add_argument("client", choices=["codex", "claude", "opencode"])
    hook.add_argument("event")
    args = parser.parse_args()
    isolated = _isolated_exe()
    if args.command in {"status", "benchmark", "test", "mcp", "hook"} and isolated and not environment()["installed"]:
        sys.exit(subprocess.run([str(isolated), *sys.argv[1:]]).returncode)
    if args.command == "setup":
        code = setup(args)
    elif args.command == "mcp":
        from .mcp_server import main as mcp_main
        mcp_main()
        return
    elif args.command == "hook":
        try:
            payload = json.load(sys.stdin)
            _json(run_hook(args.client, args.event, payload if isinstance(payload, dict) else {}))
        except Exception:
            print("{}")
        return
    elif args.command == "doctor":
        _json(doctor())
        code = 0
    elif args.command == "status":
        try:
            _json(request("status", start=False))
        except Exception:
            from .policy import DecisionEngine
            _json(DecisionEngine(load_config()).status())
        code = 0
    elif args.command == "stats":
        try:
            _json(request("stats", start=False))
        except Exception:
            from .config import Config
            from .daemon import METRICS
            from .policy import DecisionEngine
            try:
                saved = json.loads(METRICS.read_text())
            except (OSError, ValueError):
                saved = DecisionEngine(Config()).stats()
            _json(saved)
        code = 0
    elif args.command == "benchmark":
        _json(benchmark())
        code = 0
    elif args.command == "test":
        from .policy import DecisionEngine
        engine = DecisionEngine(load_config())
        engine.runtime.load()
        out = engine.decide("next_action", {"current_phase": "repository_inspection", "language": "python"})
        _json(out)
        code = 0 if out.get("decision") not in {"defer_to_agent", None} else 1
    elif args.command in {"enable", "disable"}:
        from .config import CONFIG_FILE
        write_default()
        lines = CONFIG_FILE.read_text().splitlines()
        lines = [f"enabled = {'true' if args.command == 'enable' else 'false'}" if line.startswith("enabled =") else line for line in lines]
        CONFIG_FILE.write_text("\n".join(lines) + "\n")
        try:
            request("shutdown", start=False, timeout=1)
        except Exception:
            pass
        print(args.command + "d")
        code = 0
    elif args.command == "configure":
        write_default()
        print(CONFIG_FILE)
        code = 0
    elif args.command == "uninstall":
        from .integrations import MANIFEST
        for adapter in ADAPTERS:
            adapter.uninstall()
        try:
            request("shutdown", start=False, timeout=1)
        except Exception:
            pass
        if args.remove_runtime:
            venv = Path.home() / ".local/share/laya-agent/venv"
            if (venv / ".laya-agent-owned").exists():
                shutil.rmtree(venv)
        if args.remove_model_cache:
            if load_config().model == "aac6fef/laya-mlx":
                hub = Path(os.environ.get("HF_HUB_CACHE", Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub"))
                shutil.rmtree(hub / "models--aac6fef--laya-mlx", ignore_errors=True)
        if args.remove_config:
            CONFIG_FILE.unlink(missing_ok=True)
            MANIFEST.unlink(missing_ok=True)
            (STATE_DIR / "stats.json").unlink(missing_ok=True)
            (STATE_DIR / "events.jsonl").unlink(missing_ok=True)
        print("Removed laya-agent integrations and selected owned data.")
        code = 0
    sys.exit(code)


if __name__ == "__main__":
    main()
