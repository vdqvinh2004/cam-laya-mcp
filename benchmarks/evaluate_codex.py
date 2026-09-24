#!/usr/bin/env python3
"""Run paired Codex smoke tasks with cam-laya hooks/MCP enabled and disabled."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import selectors
import shlex
import shutil
import signal
import statistics
import subprocess
import tempfile
import time
import tomllib
import uuid

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOME = pathlib.Path.home()
CODEX_HOME = pathlib.Path(os.environ.get("CODEX_HOME", HOME / ".codex"))
TASKS = json.loads((ROOT / "benchmarks/codex_tasks.json").read_text())
CODING_TASKS = json.loads((ROOT / "benchmarks/codex_coding_tasks.json").read_text())


def toml_string(value: str) -> str:
    return json.dumps(value)


def error_category(message: str) -> str:
    value = message.lower()
    for words, category in (
        (("spawn", "start", "launch"), "server_start"),
        (("timeout", "timed out"), "timeout"),
        (("invalid", "required", "schema", "argument"), "invalid_arguments"),
        (("connect", "socket", "pipe", "closed"), "connection"),
        (("auth", "credential", "permission"), "authorization"),
    ):
        if any(word in value for word in words):
            return category
    return "other" if value else "unspecified"


def isolated_config(directory: pathlib.Path, profile: str, model: str, workdir: pathlib.Path = ROOT, reasoning_effort: str = "low") -> dict[str, str]:
    source = tomllib.loads((CODEX_HOME / "config.toml").read_text())
    laya = source.get("mcp_servers", {}).get("cam-laya-mcp")
    hooks_enabled = profile in {"hooks", "combined"}
    mcp_enabled = profile in {"mcp", "combined"}
    if (hooks_enabled or mcp_enabled) and not laya:
        raise RuntimeError("Codex cam-laya-mcp entry is required")
    (directory / "auth.json").write_bytes((CODEX_HOME / "auth.json").read_bytes())
    config = [f"model = {toml_string(model)}", f"model_reasoning_effort = {toml_string(reasoning_effort)}"]
    config.extend(("", f"[projects.{toml_string(str(workdir))}]", 'trust_level = "trusted"', "", "[features]", f"hooks = {'true' if hooks_enabled else 'false'}"))
    xdg_config = directory / "xdg-config"
    xdg_state = directory / "xdg-state"
    xdg_config.mkdir()
    xdg_state.mkdir()
    source_config = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "laya-agent/config.toml"
    if source_config.exists():
        target_config = xdg_config / "laya-agent"
        target_config.mkdir()
        shutil.copyfile(source_config, target_config / "config.toml")
    if mcp_enabled:
        config.extend(("", '[mcp_servers."cam-laya-mcp"]', 'command = "/usr/bin/env"'))
        args = [f"XDG_CONFIG_HOME={xdg_config}", f"XDG_STATE_HOME={xdg_state}", f"PYTHONPATH={ROOT / 'src'}", laya["command"], *laya.get("args", [])]
        config.append("args = " + json.dumps(args))
    (directory / "config.toml").write_text("\n".join(config) + "\n")
    if hooks_enabled:
        hooks = json.loads((CODEX_HOME / "hooks.json").read_text()).get("hooks", {})
        filtered = {}
        binary = laya["command"]
        prefix = shlex.join(("/usr/bin/env", f"XDG_CONFIG_HOME={xdg_config}", f"XDG_STATE_HOME={xdg_state}", f"PYTHONPATH={ROOT / 'src'}"))
        for event, rows in hooks.items():
            if event == "UserPromptSubmit":
                continue
            selected = []
            for row in rows:
                commands = [
                    {**hook, "command": f"{prefix} {hook['command']}"}
                    for hook in row.get("hooks", [])
                    if hook.get("command", "").startswith(binary + " hook ")
                ]
                if commands:
                    selected.append({**{k: v for k, v in row.items() if k != "hooks"}, "hooks": commands})
            if selected:
                filtered[event] = selected
        (directory / "hooks.json").write_text(json.dumps({"hooks": filtered}))
    return {"CODEX_HOME": str(directory), "XDG_CONFIG_HOME": str(xdg_config), "XDG_STATE_HOME": str(xdg_state)}


def summarize_events(output: str) -> dict:
    totals = {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}
    tool_calls: dict[str, int] = {}
    tool_errors = 0
    tool_error_types: dict[str, int] = {}
    tool_shapes: dict[str, int] = {}
    tool_error_details: list[str] = []
    tool_outcomes: dict[str, int] = {}
    tool_counts: dict[str, int] = {}
    item_types: dict[str, int] = {}
    test_commands = 0
    final_text = ""
    errors = []
    for line in output.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage", {})
            for key in totals:
                value = usage.get(key)
                if isinstance(value, int):
                    totals[key] += value
        item = event.get("item", {})
        kind = item.get("type", "unknown")
        if kind not in {"agent_message", "reasoning", "mcp_tool_call"} and item.get("status") != "in_progress":
            item_types[kind] = item_types.get(kind, 0) + 1
        if kind != "mcp_tool_call" and item.get("status") != "in_progress" and kind in {"command_execution", "local_shell_call"}:
            tool_counts[kind] = tool_counts.get(kind, 0) + 1
        if kind != "mcp_tool_call" and item.get("status") != "in_progress":
            commands = []
            def collect_commands(value):
                if isinstance(value, dict):
                    commands.extend(v for k, v in value.items() if k in {"command", "cmd"} and isinstance(v, str))
                    commands.extend(" ".join(v) for k, v in value.items() if k in {"command", "cmd"} and isinstance(v, list) and all(isinstance(arg, str) for arg in v))
                    for nested in value.values():
                        collect_commands(nested)
                elif isinstance(value, list):
                    for nested in value:
                        collect_commands(nested)
            collect_commands(item)
            test_commands += any(re.search(r"\b(pytest|npm\s+test|cargo\s+test|go\s+test|vitest)\b", cmd) for cmd in commands)
        if kind == "mcp_tool_call":
            if item.get("status") == "in_progress":
                continue
            name = item.get("tool", "unknown")
            tool_calls[name] = tool_calls.get(name, 0) + 1
            result = item.get("result", {})
            shape = f"status={item.get('status')};keys={','.join(sorted(item))};result={type(result).__name__}"
            if isinstance(result, dict):
                shape += f";keys={','.join(sorted(result))};content={type(result.get('content')).__name__}"
                structured = result.get("structured_content") or result.get("structuredContent") or {}
                if isinstance(structured, dict) and structured:
                    outcome = str(structured.get("reason_code", structured.get("decision", structured.get("risk", "unknown"))))
                    tool_outcomes[outcome] = tool_outcomes.get(outcome, 0) + 1
                else:
                    structured = {}
                content = result.get("content", [])
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        try:
                            value = json.loads(block["text"])
                        except json.JSONDecodeError:
                            continue
                        if isinstance(value, dict):
                            outcome = str(value.get("reason_code", value.get("decision", value.get("risk", "unknown"))))
                            tool_outcomes[outcome] = tool_outcomes.get(outcome, 0) + 1
                shape += f";structured_keys={','.join(sorted(structured))}"
            tool_shapes[shape] = tool_shapes.get(shape, 0) + 1
            failed = item.get("status") == "failed" or isinstance(result, dict) and bool(result.get("isError"))
            if failed:
                tool_errors += 1
                content = result.get("content", []) if isinstance(result, dict) else []
                message = " ".join((json.dumps(item.get("error", "")), *(str(block.get("text", "")) for block in content if isinstance(block, dict))))
                category = error_category(message)
                tool_error_types[category] = tool_error_types.get(category, 0) + 1
                if os.environ.get("CAM_LAYA_EVAL_DEBUG"):
                    tool_error_details.append(str(item.get("error", message))[:500])
        if item.get("type") == "agent_message":
            final_text = item.get("text", final_text)
        if event.get("type") == "error":
            errors.append(str(event.get("message", "error")))
    result = {**totals, "mcp_tool_calls": tool_calls, "mcp_tool_errors": tool_errors, "mcp_tool_error_types": tool_error_types, "mcp_tool_shapes": tool_shapes, "mcp_tool_outcomes": tool_outcomes, "tool_calls": tool_counts, "item_types": item_types, "test_command_calls": test_commands, "response_present": bool(final_text.strip()), "_answer_text": final_text, "errors": errors}
    if tool_error_details:
        result["mcp_tool_error_details"] = tool_error_details
    return result


def read_decisions(env: dict[str, str], run_id: str) -> tuple[list[dict], list[dict]]:
    directory = pathlib.Path(env["XDG_STATE_HOME"]) / "laya-agent"
    def rows(name: str) -> list[dict]:
        found = []
        for path in (directory / name, (directory / name).with_suffix(".jsonl.1")):
            if path.exists():
                for line in path.read_text().splitlines():
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if event.get("run_id") == run_id:
                        found.append(event)
        return found
    return rows("events.jsonl"), rows("client-events.jsonl")


def set_trial_run_id(env: dict[str, str], run_id: str) -> None:
    home = pathlib.Path(env["CODEX_HOME"])
    config = home / "config.toml"
    lines = []
    for line in config.read_text().splitlines():
        if line.startswith("args = "):
            args = [value for value in json.loads(line.removeprefix("args = ")) if not value.startswith("CAM_LAYA_RUN_ID=")]
            args.insert(3, f"CAM_LAYA_RUN_ID={run_id}")
            line = "args = " + json.dumps(args)
        lines.append(line)
    config.write_text("\n".join(lines) + "\n")
    hooks_path = home / "hooks.json"
    if hooks_path.exists():
        hooks = json.loads(hooks_path.read_text())
        for groups in hooks.get("hooks", {}).values():
            for group in groups:
                for hook in group.get("hooks", []):
                    command = re.sub(r"CAM_LAYA_RUN_ID=[a-f0-9]+ ", "", hook["command"])
                    hook["command"] = command.replace("/usr/bin/env ", f"/usr/bin/env CAM_LAYA_RUN_ID={run_id} ", 1)
        hooks_path.write_text(json.dumps(hooks))


def run_codex(command: list[str], env: dict[str, str]) -> tuple[int, float, float | None, str, str]:
    started = time.perf_counter()
    lines = []
    first_response = None
    with tempfile.TemporaryFile(mode="w+t") as stderr:
        process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=stderr, text=True, bufsize=1)
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout, selectors.EVENT_READ)
            while process.poll() is None or selector.get_map():
                if time.perf_counter() - started > 600:
                    process.kill()
                    break
                for key, _ in selector.select(timeout=0.5):
                    line = key.fileobj.readline()
                    if not line:
                        selector.unregister(key.fileobj)
                        continue
                    lines.append(line)
                    if first_response is None:
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        item = event.get("item", {})
                        if item.get("type") == "agent_message" and item.get("text"):
                            first_response = round((time.perf_counter() - started) * 1000, 2)
        process.wait()
        elapsed = round(time.perf_counter() - started, 2)
        stderr.seek(0)
        error_text = stderr.read()
    return process.returncode, elapsed, first_response, "".join(lines), error_text


def run_one(task: dict, profile: str, model: str, env: dict[str, str], workdir: pathlib.Path = ROOT, cohort: str = "mixed") -> dict:
    run_id = uuid.uuid4().hex
    trial_env = {**env, "CAM_LAYA_RUN_ID": run_id}
    set_trial_run_id(env, run_id)
    command = [shutil.which("codex") or "codex", "exec", "--ephemeral", "--json", "--sandbox", "workspace-write" if "files" in task else "read-only"]
    if "files" in task:
        command.append("--skip-git-repo-check")
    if profile in {"hooks", "combined"}:
        command.append("--dangerously-bypass-hook-trust")
    prompt = task["prompt"]
    if "files" not in task:
        prompt += "\nAnswer from these facts only. Do not inspect the repository or run shell commands. Call only an MCP tool explicitly requested above."
    command.extend(("-C", str(workdir), "-m", model, prompt))
    exit_code, elapsed, first_response, output, stderr = run_codex(command, trial_env)
    decisions, client_events = read_decisions(env, run_id) if profile != "baseline" else ([], [])
    inferences = [row["inference_ms"] for row in decisions if isinstance(row.get("inference_ms"), (int, float))]
    stats = {
        "laya_decisions": sum(row.get("outcome") == "model" for row in decisions),
        "hook_decisions": sum(row.get("source") == "hook" for row in decisions),
        "mcp_decisions": sum(row.get("source") == "mcp" for row in decisions),
        "cache_hits": sum(row.get("outcome") == "cache" for row in decisions),
        "laya_failures": sum(row.get("outcome") == "failure" for row in decisions),
        "decisions_by_policy_delta": {policy: sum(row.get("policy") == policy for row in decisions) for policy in ("route_task", "next_action", "test_decision", "review_decision", "risk_check")},
        "average_latency_ms": round(statistics.mean(inferences), 2) if inferences else None,
        "decision_events": decisions,
        "client_events": client_events,
    }
    summary = summarize_events(output)
    answer_text = summary.pop("_answer_text").lower()
    test_evidence = "command_event" if summary["test_command_calls"] else None
    if task["id"] == "review_hint" and not test_evidence:
        if summary["tool_calls"].get("command_execution"):
            test_evidence = "only_requested_command"
        elif stats.get("decisions_by_policy_delta", {}).get("review_decision", 0):
            test_evidence = "post_test_hook"
    required_tests = task.get("required_test_commands", 0)
    required_mcp = task.get("required_mcp_calls", 0) if profile in {"mcp", "combined"} else 0
    actual_mcp = sum(summary["mcp_tool_calls"].values())
    if "files" in task:
        check = subprocess.run(task["check"], cwd=workdir, capture_output=True, text=True, timeout=60)
        changed = {name for name, original in task["files"].items() if (workdir / name).exists() and (workdir / name).read_text() != original}
        missing = [name for name in task["files"] if not (workdir / name).exists()]
        added = [str(path.relative_to(workdir)) for path in (workdir / "bench_case").rglob("*") if path.is_file() and path.suffix == ".py" and str(path.relative_to(workdir)) not in task["files"]]
        rubric = changed == set(task["allowed_changes"]) and not missing and not added
        summary.update(check_pass=check.returncode == 0, check_exit_code=check.returncode, patch_rubric=rubric)
        summary["quality_ok"] = exit_code == 0 and check.returncode == 0 and rubric and summary["mcp_tool_errors"] == 0
        marker_match = None
        test_evidence = "runner_check"
    else:
        marker_match = task["marker"].lower() in answer_text
        summary["quality_ok"] = marker_match and (summary["test_command_calls"] >= required_tests or test_evidence is not None) and summary["mcp_tool_errors"] == 0 and actual_mcp >= required_mcp
    return {
        "task": task["id"], "condition": profile, "cohort": cohort, "eligible": task.get("eligible"),
        "exit_code": exit_code, "elapsed_seconds": elapsed, "first_response_ms": first_response,
        **summary, "answer_marker_match": marker_match, "test_evidence": test_evidence, "laya_stats_delta": stats,
        "stderr_present": bool(stderr.strip()),
        "stderr_category": error_category(stderr) if stderr.strip() else None,
        "error": stderr.strip()[:500] if exit_code else None,
    }


def stop_daemon(env: dict[str, str]) -> None:
    state = pathlib.Path(env["XDG_STATE_HOME"]) / "laya-agent"
    socket_path = state / "agent.sock"
    try:
        import socket
        with socket.socket(socket.AF_UNIX) as client:
            client.settimeout(1)
            client.connect(str(socket_path))
            client.sendall(b'{"op":"shutdown"}\n')
            client.recv(1024)
        for _ in range(50):
            if not socket_path.exists():
                return
            time.sleep(0.05)
    except OSError:
        pass
    try:
        os.kill(int((state / "agent.pid").read_text()), signal.SIGTERM)
    except (FileNotFoundError, ValueError, ProcessLookupError):
        pass


def preload_daemon(env: dict[str, str]) -> None:
    binary = tomllib.loads((CODEX_HOME / "config.toml").read_text())["mcp_servers"]["cam-laya-mcp"]["command"]
    python = str(pathlib.Path(binary).with_name("python"))
    process = subprocess.run(
        [python, "-c", 'from laya_agent.daemon import request; assert request("preload", timeout=180)["model_loaded"]'],
        env={**os.environ, **env, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True, timeout=200,
    )
    if process.returncode:
        raise RuntimeError(f"Laya preload failed: {error_category(process.stderr)}")


def prepare_coding_trial(snapshot: pathlib.Path, task: dict, destination: pathlib.Path) -> None:
    shutil.copytree(snapshot, destination)
    for name, content in task["files"].items():
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    


def trust_workdir(env: dict[str, str], workdir: pathlib.Path) -> None:
    with (pathlib.Path(env["CODEX_HOME"]) / "config.toml").open("a") as config:
        config.write(f'\n[projects.{toml_string(str(workdir))}]\ntrust_level = "trusted"\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--suite", choices=("diagnostic", "coding"), default="diagnostic")
    parser.add_argument("--task", action="append")
    parser.add_argument("--condition", choices=("baseline", "with_cam_laya", "all"), default="all")
    parser.add_argument("--profiles", nargs="+", choices=("baseline", "hooks", "mcp", "combined"))
    parser.add_argument("--cohort", choices=("mixed", "cold", "warm", "both"), default="mixed")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("docs/codex-efficacy-results.json"))
    parser.add_argument("--model", default=tomllib.loads((CODEX_HOME / "config.toml").read_text()).get("model", "gpt-6-luna"))
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"), default="low")
    args = parser.parse_args()
    if args.self_check:
        sample = "\n".join((
            '{"type":"turn.completed","usage":{"input_tokens":7,"cached_input_tokens":2,"output_tokens":3}}',
            '{"type":"item.completed","item":{"type":"mcp_tool_call","tool":"laya_route_task"}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}',
        ))
        parsed = summarize_events(sample)
        assert parsed["input_tokens"] == 7 and parsed["output_tokens"] == 3
        assert parsed["mcp_tool_calls"] == {"laya_route_task": 1} and parsed["mcp_tool_errors"] == 0 and parsed["response_present"]
        with tempfile.TemporaryDirectory(prefix="cly-check-", dir="/tmp") as directory:
            events = pathlib.Path(directory) / "laya-agent/events.jsonl"
            events.parent.mkdir()
            events.write_text('{"run_id":"a","outcome":"model","inference_ms":12}\n{"run_id":"b","outcome":"cache"}\n')
            found, clients = read_decisions({"XDG_STATE_HOME": directory}, "a")
            assert len(found) == 1 and found[0]["inference_ms"] == 12 and not clients
            config = pathlib.Path(directory) / "config.toml"
            config.write_text('args = ["XDG_CONFIG_HOME=/tmp/x", "XDG_STATE_HOME=/tmp/y", "PYTHONPATH=/tmp/z", "/tmp/laya", "mcp"]\n')
            set_trial_run_id({"CODEX_HOME": directory}, "a" * 32)
            assert tomllib.loads(config.read_text())["args"][3] == "CAM_LAYA_RUN_ID=" + "a" * 32
        print("self-check passed")
        return
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    task_set = CODING_TASKS if args.suite == "coding" else TASKS
    unknown = set(args.task or ()) - {task["id"] for task in task_set}
    if unknown:
        parser.error(f"unknown task IDs: {', '.join(sorted(unknown))}")
    tasks = [t for t in task_set if not args.task or t["id"] in args.task]
    results = []
    profiles = args.profiles or (("baseline", "combined") if args.condition == "all" else ("combined" if args.condition == "with_cam_laya" else "baseline",))
    cohorts = ("cold", "warm") if args.cohort == "both" else (args.cohort,)
    with tempfile.TemporaryDirectory(prefix="cly-", dir="/tmp") as temporary:
        snapshot = pathlib.Path(temporary) / "snapshot"
        if args.suite == "coding":
            shutil.copytree(ROOT, snapshot, ignore=shutil.ignore_patterns(".git", ".venv", "venv", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", ".codebase-memory"))
        environments = {}
        for profile in profiles:
            directory = pathlib.Path(temporary) / profile
            directory.mkdir()
            environment = {**os.environ, **isolated_config(directory, profile, args.model, reasoning_effort=args.reasoning_effort)}
            environments[profile] = environment
        try:
            for repetition in range(args.repetitions):
                for task_index, task in enumerate(tasks):
                    for cohort in cohorts:
                        offset = (repetition + task_index) % len(profiles)
                        order = (*profiles[offset:], *profiles[:offset])
                        for position, profile in enumerate(order, 1):
                            workdir = ROOT
                            if args.suite == "coding":
                                workdir = pathlib.Path(temporary) / f"work-{len(results)}"
                                prepare_coding_trial(snapshot, task, workdir)
                                trust_workdir(environments[profile], workdir)
                            if cohort == "cold" and profile != "baseline":
                                stop_daemon(environments[profile])
                            elif cohort == "warm" and profile != "baseline":
                                preload_daemon(environments[profile])
                            row = run_one(task, profile, args.model, environments[profile], workdir=workdir, cohort=cohort)
                            row.update(repetition=repetition + 1, run_order=position)
                            results.append(row)
                            print(json.dumps(row), flush=True)
        finally:
            for profile in profiles:
                if profile != "baseline":
                    stop_daemon(environments[profile])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"model": args.model, "reasoning_effort": args.reasoning_effort, "results": results}, indent=2) + "\n")
    for condition in profiles:
        rows = [r for r in results if r["condition"] == condition]
        print(json.dumps({
            "summary": condition,
            "runs": len(rows),
            "median_elapsed_seconds": statistics.median(r["elapsed_seconds"] for r in rows) if rows else None,
            "input_tokens": sum(r["input_tokens"] for r in rows),
            "output_tokens": sum(r["output_tokens"] for r in rows),
            "mcp_tool_calls": sum(sum(r["mcp_tool_calls"].values()) for r in rows),
            "test_command_calls": sum(r["test_command_calls"] for r in rows),
            "answer_marker_matches": sum(r["answer_marker_match"] is True for r in rows),
            "quality_passes": sum(r["quality_ok"] for r in rows),
            "laya_stats": {k: sum(r["laya_stats_delta"].get(k, 0) or 0 for r in rows) for k in ("laya_decisions", "hook_decisions", "mcp_decisions", "cache_hits", "laya_failures")},
            "policy_decisions": {policy: sum(r["laya_stats_delta"].get("decisions_by_policy_delta", {}).get(policy, 0) for r in rows) for policy in ("route_task", "next_action", "test_decision", "review_decision", "risk_check")},
        }))


if __name__ == "__main__":
    main()
