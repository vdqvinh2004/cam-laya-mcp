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
CONTEXT_TASKS = json.loads((ROOT / "benchmarks/codex_context_tasks.json").read_text())["tasks"]
TEST_COMMAND = re.compile(r"\b(pytest|npm\s+test|cargo\s+test|go\s+test|vitest|python(?:3(?:\.\d+)?)?\s+-m\s+unittest)\b")
DISCOVERY_COMMAND = re.compile(r"\b(ls|find|grep|rg|fd|glob|cat|head|tail|tree|file|wc|sed|awk|ls-files|git\s+ls-files)\b")
REVIEW_COMMAND = re.compile(r"\bgit\s+diff(?:\s|$)", re.IGNORECASE)
HOOK_PROFILES = {
    "hooks": ("SessionStart", "PreToolUse", "PostToolUse"),
    "hooks_session_pre": ("SessionStart", "PreToolUse"),
    "hooks_pre_post": ("PreToolUse", "PostToolUse"),
    "hooks_pre": ("PreToolUse",),
    "context": ("PreToolUse", "UserPromptSubmit"),
}


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


def is_laya_hook_command(command: str, binary: str) -> bool:
    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if parts and parts[0] == "/usr/bin/env":
        parts = parts[1:]
        while parts and "=" in parts[0]:
            parts = parts[1:]
    return len(parts) == 4 and parts[0] == binary and parts[1:3] == ["hook", "codex"] and parts[3] in {"SessionStart", "PreToolUse", "PostToolUse", "UserPromptSubmit"}


def laya_only_hooks(hooks: dict, binary: str, prefix: str, events: tuple[str, ...] | None = None) -> dict:
    filtered = {}
    for event, rows in hooks.items():
        if event == "UserPromptSubmit" or (events is not None and event not in events):
            continue
        selected = []
        for row in rows:
            commands = [
                {**hook, "command": f"{prefix} {hook['command']}"}
                for hook in row.get("hooks", [])
                if is_laya_hook_command(hook.get("command", ""), binary)
            ]
            if commands:
                selected.append({**{k: v for k, v in row.items() if k != "hooks"}, "hooks": commands})
        if selected:
            filtered[event] = selected
    return filtered


def audit_isolation(env: dict[str, str], profile: str, workdir: pathlib.Path, binary: str | None = None) -> dict:
    home = pathlib.Path(env["CODEX_HOME"]).resolve()
    hook_events = HOOK_PROFILES.get(profile, HOOK_PROFILES["hooks"] if profile == "combined" else ())
    expected_hooks = bool(hook_events)
    expected_hook_events = set(hook_events) or None
    expected_servers = {"cam-laya-mcp"} if profile in {"mcp", "combined"} else set()
    if binary is None:
        binary = env.get("CAM_LAYA_EXECUTABLE")
    if binary is None and (expected_hooks or expected_servers):
        source = tomllib.loads((CODEX_HOME / "config.toml").read_text())
        binary = str(source.get("mcp_servers", {}).get("cam-laya-mcp", {}).get("command", ""))
    binary = binary or ""
    config = tomllib.loads((home / "config.toml").read_text())
    hooks_path = home / "hooks.json"
    hooks = json.loads(hooks_path.read_text()).get("hooks", {}) if hooks_path.exists() else {}
    commands = [hook.get("command", "") for rows in hooks.values() for row in rows for hook in row.get("hooks", [])]
    servers = set(config.get("mcp_servers", {}))
    hook_enabled = config.get("features", {}).get("hooks") is True
    project_configs = [path / ".codex" for path in (workdir, *workdir.parents) if (path / ".codex").exists()]
    problems = []
    if home == CODEX_HOME.resolve():
        problems.append("CODEX_HOME is not temporary")
    if set(config) - {"model", "model_reasoning_effort", "projects", "features", "mcp_servers"}:
        problems.append("unexpected Codex config source")
    if servers != expected_servers:
        problems.append(f"unexpected MCP servers: {sorted(servers)}")
    if hook_enabled != expected_hooks or hooks_path.exists() != expected_hooks:
        problems.append("hook setting or manifest does not match profile")
    if config.get("features", {}).get("plugins") is not False:
        problems.append("plugin execution is not disabled")
    if config.get("features", {}).get("remote_plugin") is not False:
        problems.append("remote plugin catalog is not disabled")
    if expected_hooks and (not commands or any(not is_laya_hook_command(command, binary) for command in commands)):
        problems.append("hook profile contains no valid cam-laya-mcp hooks or contains another command")
    if expected_hook_events and set(hooks) != expected_hook_events:
        problems.append(f"hook events do not match profile: {sorted(hooks)}")
    laya_server = config.get("mcp_servers", {}).get("cam-laya-mcp", {})
    if expected_servers and (laya_server.get("command") != "/usr/bin/env" or binary not in laya_server.get("args", [])):
        problems.append("cam-laya-mcp server command does not match the configured executable")
    if not expected_hooks and commands:
        problems.append("hooks found in a hook-free profile")
    if project_configs:
        problems.append("project .codex config is present")
    for key in ("XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        try:
            pathlib.Path(env[key]).resolve().relative_to(home)
        except (KeyError, ValueError):
            problems.append(f"{key} is outside temporary CODEX_HOME")
    if problems:
        raise RuntimeError("isolation audit failed: " + "; ".join(problems))
    return {
        "static_pass": True,
        "profile": profile,
        "mcp_servers": sorted(servers),
        "hooks_enabled": hook_enabled,
        "plugins_disabled": True,
        "remote_plugin_catalog_disabled": True,
        "hook_command_count": len(commands),
        "hook_events": sorted(hooks),
        "hook_commands_cam_laya_only": all(is_laya_hook_command(command, binary) for command in commands),
        "project_codex_config_absent": True,
    }


def isolated_config(directory: pathlib.Path, profile: str, model: str, workdir: pathlib.Path = ROOT, reasoning_effort: str = "low", laya_executable: str | None = None, post_test_guidance: bool = False) -> dict[str, str]:
    source = tomllib.loads((CODEX_HOME / "config.toml").read_text())
    laya = source.get("mcp_servers", {}).get("cam-laya-mcp")
    hooks_enabled = profile in HOOK_PROFILES or profile == "combined"
    mcp_enabled = profile in {"mcp", "combined"}
    binary = laya_executable or (laya or {}).get("command") or str(ROOT / ".venv/bin/cam-laya-mcp")
    if (hooks_enabled or mcp_enabled) and not pathlib.Path(binary).is_file():
        raise RuntimeError("cam-laya-mcp executable is required; pass --laya-executable")
    laya_args = laya.get("args", []) if laya and not laya_executable else ["mcp"]
    (directory / "auth.json").write_bytes((CODEX_HOME / "auth.json").read_bytes())
    config = [f"model = {toml_string(model)}", f"model_reasoning_effort = {toml_string(reasoning_effort)}"]
    config.extend(("", f"[projects.{toml_string(str(workdir))}]", 'trust_level = "trusted"', "", "[features]", f"hooks = {'true' if hooks_enabled else 'false'}", "plugins = false", "remote_plugin = false"))
    xdg_config = directory / "xdg-config"
    xdg_state = directory / "xdg-state"
    xdg_config.mkdir()
    xdg_state.mkdir()
    source_config = pathlib.Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "laya-agent/config.toml"
    target_config = xdg_config / "laya-agent"
    target_config.mkdir()
    if source_config.exists():
        shutil.copyfile(source_config, target_config / "config.toml")
    config_path = target_config / "config.toml"
    config_lines = config_path.read_text().splitlines() if config_path.exists() else []
    for key, value in (("post_test_guidance", post_test_guidance), ("context_hint", profile == "context")):
        setting = f"{key} = {str(value).lower()}"
        setting_line = next((i for i, line in enumerate(config_lines) if re.match(rf"\s*{key}\s*=", line)), None)
        if setting_line is None:
            setting_line = next((i for i, line in enumerate(config_lines) if line.lstrip().startswith("[")), len(config_lines))
            config_lines.insert(setting_line, setting)
        else:
            config_lines[setting_line] = setting
    config_path.write_text("\n".join(config_lines) + "\n")
    if mcp_enabled:
        config.extend(("", '[mcp_servers."cam-laya-mcp"]', 'command = "/usr/bin/env"'))
        args = [f"XDG_CONFIG_HOME={xdg_config}", f"XDG_STATE_HOME={xdg_state}", f"PYTHONPATH={ROOT / 'src'}", binary, *laya_args]
        config.append("args = " + json.dumps(args))
    (directory / "config.toml").write_text("\n".join(config) + "\n")
    if hooks_enabled:
        hooks = json.loads((CODEX_HOME / "hooks.json").read_text()).get("hooks", {})
        prefix = shlex.join(("/usr/bin/env", f"XDG_CONFIG_HOME={xdg_config}", f"XDG_STATE_HOME={xdg_state}", f"PYTHONPATH={ROOT / 'src'}"))
        events = HOOK_PROFILES.get(profile, HOOK_PROFILES["hooks"])
        filtered = laya_only_hooks(hooks, binary, prefix, events)
        for event in events:
            if event not in filtered:
                group = {"hooks": [{"type": "command", "command": shlex.join((*shlex.split(prefix), binary, "hook", "codex", event)), "timeout": 5}]}
                if event == "PreToolUse":
                    group["matcher"] = "Bash|bash|exec_command|command_execution|Read|read|read_file"
                filtered[event] = [group]
        (directory / "hooks.json").write_text(json.dumps({"hooks": filtered}))
    return {"CODEX_HOME": str(directory), "XDG_CONFIG_HOME": str(xdg_config), "XDG_STATE_HOME": str(xdg_state), "CAM_LAYA_EXECUTABLE": binary}


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
    discovery_action_calls = 0
    post_test_diff_actions = 0
    post_test_file_changes = 0
    passed_test_seen = False
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
        if kind == "file_change" and item.get("status") != "in_progress" and passed_test_seen:
            post_test_file_changes += 1
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
            test_commands += any(TEST_COMMAND.search(cmd) for cmd in commands)
            discovery_action_calls += sum(bool(DISCOVERY_COMMAND.search(cmd)) and not TEST_COMMAND.search(cmd) for cmd in commands)
            command_succeeded = item.get("status") != "failed" and item.get("exit_code") in (None, 0)
            for command in commands:
                test_match = TEST_COMMAND.search(command)
                review_match = REVIEW_COMMAND.search(command)
                if test_match and command_succeeded:
                    if review_match and review_match.start() > test_match.end():
                        post_test_diff_actions += 1
                    passed_test_seen = True
                elif review_match and passed_test_seen:
                    post_test_diff_actions += 1
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
    result = {**totals, "mcp_tool_calls": tool_calls, "mcp_tool_errors": tool_errors, "mcp_tool_error_types": tool_error_types, "mcp_tool_shapes": tool_shapes, "mcp_tool_outcomes": tool_outcomes, "tool_calls": tool_counts, "item_types": item_types, "test_command_calls": test_commands, "discovery_action_calls": discovery_action_calls, "post_test_diff_actions": post_test_diff_actions, "post_test_file_change_items": post_test_file_changes, "response_present": bool(final_text.strip()), "_answer_text": final_text, "errors": errors}
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
                    command = re.sub(r"(?:CAM_LAYA_EVAL_HOOK_LOG=1 |CAM_LAYA_RUN_ID=[a-f0-9]+ )", "", hook["command"])
                    hook["command"] = command.replace("/usr/bin/env ", f"/usr/bin/env CAM_LAYA_EVAL_HOOK_LOG=1 CAM_LAYA_RUN_ID={run_id} ", 1)
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
    isolation = audit_isolation(env, profile, workdir)
    command = [shutil.which("codex") or "codex", "exec", "--ephemeral", "--json", "--strict-config", "--disable", "plugins", "--disable", "remote_plugin", "--sandbox", "workspace-write" if "files" in task else "read-only"]
    command.append("--skip-git-repo-check")
    if profile in {*HOOK_PROFILES, "combined"}:
        command.append("--dangerously-bypass-hook-trust")
    prompt = task["prompt"]
    if "files" not in task:
        prompt += "\nAnswer from these facts only. Do not inspect the repository or run shell commands. Call only an MCP tool explicitly requested above."
    command.extend(("-C", str(workdir), "-m", model, prompt))
    exit_code, elapsed, first_response, output, stderr = run_codex(command, trial_env)
    try:
        audit_isolation(env, profile, workdir)
        isolation["post_run_static_pass"] = True
    except RuntimeError as error:
        isolation["post_run_static_pass"] = False
        isolation["post_run_error"] = str(error).removeprefix("isolation audit failed: ")
    decisions, client_events = read_decisions(env, run_id) if profile != "baseline" else ([], [])
    hook_log = pathlib.Path(env["XDG_STATE_HOME"]) / "laya-agent/hook-calls.jsonl"
    hook_calls = 0
    if profile != "baseline" and hook_log.exists():
        for line in hook_log.read_text().splitlines():
            try:
                hook_calls += json.loads(line).get("run_id") == run_id
            except json.JSONDecodeError:
                continue
    inferences = [row["inference_ms"] for row in decisions if isinstance(row.get("inference_ms"), (int, float))]
    lookups = [row["lookup_ms"] for row in decisions if isinstance(row.get("lookup_ms"), (int, float))]
    sanitized = [{key: value for key, value in row.items() if key != "hint_files"} for row in decisions]
    stats = {
        "laya_decisions": sum(row.get("outcome") == "model" for row in decisions),
        "hook_decisions": sum(row.get("source") == "hook" for row in decisions),
        "mcp_decisions": sum(row.get("source") == "mcp" for row in decisions),
        "cache_hits": sum(row.get("outcome") == "cache" for row in decisions),
        "laya_failures": sum(row.get("outcome") == "failure" for row in decisions),
        "context_hints": sum(row.get("policy") == "context_hint" for row in decisions),
        "context_lookup_ms": round(statistics.mean(lookups), 2) if lookups else None,
        "context_hint_chars": sum(row.get("hint_chars", 0) for row in decisions if isinstance(row.get("hint_chars"), int)),
        "decisions_by_policy_delta": {policy: sum(row.get("policy") == policy for row in decisions) for policy in ("route_task", "next_action", "test_decision", "review_decision", "risk_check", "context_hint")},
        "average_latency_ms": round(statistics.mean(inferences), 2) if inferences else None,
        "decision_events": sanitized,
        "client_events": client_events,
    }
    summary = summarize_events(output)
    observed_mcp = summary["mcp_tool_calls"]
    unexpected_mcp = observed_mcp if profile in {"baseline", *HOOK_PROFILES} else {}
    isolation.update(
        passed=isolation.get("post_run_static_pass", False) and not unexpected_mcp,
        observed_mcp_tool_calls=observed_mcp,
        unexpected_mcp_tool_calls=unexpected_mcp,
    )
    review_hints = [row for row in decisions if row.get("policy") == "review_decision" and row.get("decision") == "self_review"]
    summary["review_hint_count"] = len(review_hints)
    summary["review_action_after_hint"] = bool(review_hints and summary["post_test_diff_actions"])
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
        independent_check = subprocess.run(task["independent_check"], cwd=workdir, capture_output=True, text=True, timeout=60) if task.get("independent_check") else None
        changed = {name for name, original in task["files"].items() if (workdir / name).exists() and (workdir / name).read_text() != original}
        hint_files = {name for row in decisions for name in (row.get("hint_files") or []) if isinstance(name, str)}
        summary.update(hinted_first_use=bool(hint_files & changed), context_hint_files=len(hint_files),
                       hint_hit_target=bool(hint_files & set(task["allowed_changes"])))
        missing = [name for name in task["files"] if not (workdir / name).exists()]
        added = [str(path.relative_to(workdir)) for path in (workdir / "bench_case").rglob("*") if path.is_file() and path.suffix == ".py" and str(path.relative_to(workdir)) not in task["files"]]
        rubric = changed == set(task["allowed_changes"]) and not missing and not added
        summary.update(check_pass=check.returncode == 0, check_exit_code=check.returncode, patch_rubric=rubric)
        if independent_check is not None:
            summary.update(independent_check_pass=independent_check.returncode == 0, independent_check_exit_code=independent_check.returncode)
        summary["quality_ok"] = isolation["passed"] and exit_code == 0 and check.returncode == 0 and (independent_check is None or independent_check.returncode == 0) and rubric and summary["mcp_tool_errors"] == 0
        marker_match = None
        test_evidence = "runner_check"
    else:
        marker_match = task["marker"].lower() in answer_text
        summary["quality_ok"] = isolation["passed"] and marker_match and (summary["test_command_calls"] >= required_tests or test_evidence is not None) and summary["mcp_tool_errors"] == 0 and actual_mcp >= required_mcp
    return {
        "task": task["id"], "condition": profile, "cohort": cohort, "eligible": task.get("eligible"),
        "hook_calls": hook_calls,
        "exit_code": exit_code, "elapsed_seconds": elapsed, "first_response_ms": first_response,
        **summary, "answer_marker_match": marker_match, "test_evidence": test_evidence, "laya_stats_delta": stats, "isolation": isolation,
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
    subprocess.run(["git", "-C", str(destination), "add", "-A"], check=True)
    subprocess.run([
        "git", "-C", str(destination), "-c", "user.name=Codex benchmark", "-c", "user.email=benchmark@localhost",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "task baseline",
    ], check=True)


def trust_workdir(env: dict[str, str], workdir: pathlib.Path) -> None:
    with (pathlib.Path(env["CODEX_HOME"]) / "config.toml").open("a") as config:
        config.write(f'\n[projects.{toml_string(str(workdir))}]\ntrust_level = "trusted"\n')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-check", action="store_true")
    parser.add_argument("--suite", choices=("diagnostic", "coding", "context"), default="diagnostic")
    parser.add_argument("--task", action="append")
    parser.add_argument("--condition", choices=("baseline", "with_cam_laya", "all"), default="all")
    parser.add_argument("--profiles", nargs="+", choices=("baseline", "hooks", "hooks_session_pre", "hooks_pre_post", "hooks_pre", "context", "mcp", "combined"))
    parser.add_argument("--cohort", choices=("mixed", "cold", "warm", "both"), default="mixed")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--output", type=pathlib.Path, default=pathlib.Path("docs/codex-efficacy-results.json"))
    parser.add_argument("--model", default=tomllib.loads((CODEX_HOME / "config.toml").read_text()).get("model", "gpt-6-luna"))
    parser.add_argument("--laya-executable", type=pathlib.Path)
    parser.add_argument("--post-test-guidance", action="store_true", help="Enable post-test guidance in the isolated Laya profile")
    parser.add_argument("--reasoning-effort", choices=("low", "medium", "high", "xhigh"), default="low")
    args = parser.parse_args()
    if args.self_check:
        sample = "\n".join((
            '{"type":"turn.completed","usage":{"input_tokens":7,"cached_input_tokens":2,"output_tokens":3}}',
            '{"type":"item.completed","item":{"type":"mcp_tool_call","tool":"laya_route_task"}}',
            '{"type":"item.completed","item":{"type":"command_execution","command":"python3 -m unittest discover -q"}}',
            '{"type":"item.completed","item":{"type":"command_execution","command":"git diff --check","exit_code":0}}',
            '{"type":"item.completed","item":{"type":"file_change","status":"completed"}}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"ok"}}',
        ))
        parsed = summarize_events(sample)
        assert parsed["input_tokens"] == 7 and parsed["output_tokens"] == 3
        assert parsed["mcp_tool_calls"] == {"laya_route_task": 1} and parsed["mcp_tool_errors"] == 0 and parsed["response_present"] and parsed["test_command_calls"] == 1 and parsed["post_test_diff_actions"] == 1 and parsed["post_test_file_change_items"] == 1
        before_test = summarize_events('\n'.join((
            '{"type":"item.completed","item":{"type":"command_execution","command":"git diff"}}',
            '{"type":"item.completed","item":{"type":"command_execution","command":"pytest","exit_code":0}}',
        )))
        failed_test = summarize_events('\n'.join((
            '{"type":"item.completed","item":{"type":"command_execution","command":"pytest","exit_code":1}}',
            '{"type":"item.completed","item":{"type":"command_execution","command":"git diff"}}',
        )))
        assert before_test["post_test_diff_actions"] == failed_test["post_test_diff_actions"] == 0
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
            binary = "/tmp/cam-laya-mcp"
            fake_hooks = {
                "SessionStart": [{"hooks": [{"command": shlex.join((binary, "hook", "codex", "SessionStart"))}]}],
                "PreToolUse": [{"hooks": [{"command": shlex.join((binary, "hook", "codex", "PreToolUse"))}]}],
                "PostToolUse": [{"hooks": [
                    {"command": shlex.join((binary, "hook", "codex", "PostToolUse"))},
                    {"command": "/tmp/other-mcp hook codex PostToolUse"},
                ]}],
            }
            prefix = "/usr/bin/env XDG_CONFIG_HOME=/tmp/cly-xdg"
            full_hooks = laya_only_hooks(fake_hooks, binary, prefix, HOOK_PROFILES["hooks"])
            filtered = laya_only_hooks(fake_hooks, binary, prefix, HOOK_PROFILES["hooks_pre_post"])
            pre_only = laya_only_hooks(fake_hooks, binary, prefix, HOOK_PROFILES["hooks_pre"])
            assert sum(len(row["hooks"]) for rows in full_hooks.values() for row in rows) == 3
            assert set(filtered) == {"PreToolUse", "PostToolUse"}
            assert sum(len(row["hooks"]) for rows in filtered.values() for row in rows) == 2
            assert set(pre_only) == {"PreToolUse"} and sum(len(row["hooks"]) for rows in pre_only.values() for row in rows) == 1
            assert all(is_laya_hook_command(hook["command"], binary) for rows in filtered.values() for row in rows for hook in row["hooks"])
            for profile in ("baseline", "hooks", "hooks_session_pre", "hooks_pre_post", "hooks_pre", "context"):
                home = pathlib.Path(directory) / profile
                home.mkdir()
                workspace = pathlib.Path(directory) / f"{profile}-work"
                workspace.mkdir()
                (home / "xdg-config").mkdir()
                (home / "xdg-state").mkdir()
                (home / "config.toml").write_text(
                    f'model = "test"\nmodel_reasoning_effort = "low"\n\n[projects.{toml_string(str(workspace))}]\ntrust_level = "trusted"\n\n[features]\nhooks = {str(profile in HOOK_PROFILES).lower()}\nplugins = false\nremote_plugin = false\n'
                )
                if profile != "baseline":
                    events = HOOK_PROFILES.get(profile, HOOK_PROFILES["hooks"])
                    hooks = laya_only_hooks(fake_hooks, binary, prefix, events)
                    for event in events:
                        if event not in hooks:
                            group = {"hooks": [{"type": "command", "command": shlex.join((*shlex.split(prefix), binary, "hook", "codex", event)), "timeout": 5}]}
                            if event == "PreToolUse":
                                group["matcher"] = "Bash|bash|exec_command|command_execution|Read|read|read_file"
                            hooks[event] = [group]
                    (home / "hooks.json").write_text(json.dumps({"hooks": hooks}))
                proof = audit_isolation({
                    "CODEX_HOME": str(home), "XDG_CONFIG_HOME": str(home / "xdg-config"), "XDG_STATE_HOME": str(home / "xdg-state"),
                }, profile, workspace, binary=binary)
                assert proof["static_pass"] and proof["mcp_servers"] == []
                assert proof["hook_command_count"] == {"baseline": 0, "hooks": 3, "hooks_session_pre": 2, "hooks_pre_post": 2, "hooks_pre": 1, "context": 2}[profile]
            discovery_sample = summarize_events('\n'.join((
                '{"type":"item.completed","item":{"type":"command_execution","command":"ls alpha"}}',
                '{"type":"item.completed","item":{"type":"command_execution","command":"find beta -name \\"*.py\\""}}',
                '{"type":"item.completed","item":{"type":"command_execution","command":"python3 -m unittest discover -q"}}',
            )))
            assert discovery_sample["discovery_action_calls"] == 2 and discovery_sample["test_command_calls"] == 1
            context_decisions = [
                {"policy": "context_hint", "outcome": "rule", "source": "hook", "lookup_ms": 12.0, "hint_chars": 120, "hint_files": ["alpha/port.py"]},
                {"policy": "risk_check", "outcome": "rule", "source": "hook"},
            ]
            assert sum(row.get("policy") == "context_hint" for row in context_decisions) == 1
            assert sum(row.get("hint_chars", 0) for row in context_decisions if isinstance(row.get("hint_chars"), int)) == 120
            assert {key for row in context_decisions for key in row} >= {"policy", "lookup_ms", "hint_chars", "hint_files"}
            stripped = [{key: value for key, value in row.items() if key != "hint_files"} for row in context_decisions]
            assert all("hint_files" not in row for row in stripped)
            snapshot = pathlib.Path(directory) / "trial-snapshot"
            snapshot.mkdir()
            subprocess.run(["git", "init", "-q", "--template=", str(snapshot)], check=True)
            subprocess.run([
                "git", "-C", str(snapshot), "-c", "user.name=Codex benchmark", "-c", "user.email=benchmark@localhost",
                "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "--allow-empty", "-qm", "baseline",
            ], check=True)
            trial = pathlib.Path(directory) / "trial"
            prepare_coding_trial(snapshot, {"files": {"bench_case/sample.py": "value = 1\n"}}, trial)
            (trial / "bench_case/sample.py").write_text("value = 2\n")
            diff = subprocess.run(["git", "-C", str(trial), "diff", "--", "bench_case/sample.py"], check=True, capture_output=True, text=True).stdout
            assert "value = 1" in diff and "value = 2" in diff
        print("self-check passed")
        return
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    task_set = {"diagnostic": TASKS, "coding": CODING_TASKS, "context": CONTEXT_TASKS}[args.suite]
    unknown = set(args.task or ()) - {task["id"] for task in task_set}
    if unknown:
        parser.error(f"unknown task IDs: {', '.join(sorted(unknown))}")
    tasks = [t for t in task_set if not args.task or t["id"] in args.task]
    results = []
    profiles = args.profiles or (("baseline", "combined") if args.condition == "all" else ("combined" if args.condition == "with_cam_laya" else "baseline",))
    cohorts = ("cold", "warm") if args.cohort == "both" else (args.cohort,)
    with tempfile.TemporaryDirectory(prefix="cly-", dir="/tmp") as temporary:
        snapshot = pathlib.Path(temporary) / "snapshot"
        scratch = pathlib.Path(temporary) / "scratch"
        scratch.mkdir()
        if args.suite in {"coding", "context"}:
            shutil.copytree(ROOT, snapshot, ignore=shutil.ignore_patterns(".git", ".codex", ".venv", "venv", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", ".codebase-memory", "benchmarks", "docs"))
            subprocess.run(["git", "init", "-q", "--template=", str(snapshot)], check=True)
            subprocess.run(["git", "-C", str(snapshot), "add", "-A"], check=True)
            subprocess.run(["git", "-C", str(snapshot), "-c", "user.name=Codex benchmark", "-c", "user.email=benchmark@localhost", "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "baseline"], check=True)
        environments = {}
        for profile in profiles:
            directory = pathlib.Path(temporary) / profile
            directory.mkdir()
            environment = {**os.environ, **isolated_config(directory, profile, args.model, workdir=scratch, reasoning_effort=args.reasoning_effort, laya_executable=str(args.laya_executable.resolve()) if args.laya_executable else None, post_test_guidance=args.post_test_guidance)}
            environments[profile] = environment
        try:
            for repetition in range(args.repetitions):
                for task_index, task in enumerate(tasks):
                    for cohort in cohorts:
                        offset = (repetition + task_index) % len(profiles)
                        order = (*profiles[offset:], *profiles[:offset])
                        for position, profile in enumerate(order, 1):
                            workdir = scratch
                            if args.suite in {"coding", "context"}:
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
    args.output.write_text(json.dumps({"model": args.model, "reasoning_effort": args.reasoning_effort, "post_test_guidance": args.post_test_guidance, "results": results}, indent=2) + "\n")
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
            "runs_with_post_test_diff": sum(r["post_test_diff_actions"] > 0 for r in rows),
            "runs_with_post_test_edits": sum(r["post_test_file_change_items"] > 0 for r in rows),
            "review_hint_trials": sum(r["review_hint_count"] > 0 for r in rows),
            "review_actions_after_hint": sum(r["review_action_after_hint"] for r in rows),
            "independent_check_passes": sum(r.get("independent_check_pass") is True for r in rows),
            "answer_marker_matches": sum(r["answer_marker_match"] is True for r in rows),
            "quality_passes": sum(r["quality_ok"] for r in rows),
            "laya_stats": {k: sum(r["laya_stats_delta"].get(k, 0) or 0 for r in rows) for k in ("laya_decisions", "hook_decisions", "mcp_decisions", "cache_hits", "laya_failures", "context_hints")},
            "policy_decisions": {policy: sum(r["laya_stats_delta"].get("decisions_by_policy_delta", {}).get(policy, 0) for r in rows) for policy in ("route_task", "next_action", "test_decision", "review_decision", "risk_check", "context_hint")},
        }))


if __name__ == "__main__":
    main()
