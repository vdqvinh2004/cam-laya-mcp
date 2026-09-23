from __future__ import annotations

import asyncio
import math
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from laya_agent.config import Config, load_config, write_default
from laya_agent.context import compact, fingerprint, git_facts, project_facts
from laya_agent.hooks import run
from laya_agent.mcp_server import mcp
from laya_agent.policy import DecisionEngine, hard_risk, should_call_laya


class FakeRuntime:
    loaded = True

    def __init__(self, choice="targeted_test", confidence=0.9, fail=False):
        self.calls = 0
        self.choice = choice
        self.confidence = confidence
        self.fail = fail

    def predict(self, state, question):
        self.calls += 1
        assert len(str(state)) < 2048
        if self.fail:
            raise RuntimeError("model crashed")
        return {"choice": self.choice, "confidence": self.confidence}


def test_compact_filters_untrusted_context():
    assert compact({"language": "python", "password": "private", "task": "secret", "changed_files": 2, "last_test_result": {"raw": "huge"}}) == {"changed_files": 2, "language": "python"}
    assert fingerprint({"a": 1, "b": 2}) == fingerprint({"b": 2, "a": 1})
    with pytest.raises(ValueError):
        compact(["wrong"])
    assert "changed_files" not in compact({"changed_files": math.nan})


def test_hard_rules_override_model():
    fake = FakeRuntime(choice="safe")
    engine = DecisionEngine(Config(), fake)
    for command in ("rm -rf /", "git push --force origin main", "terraform destroy", "DROP DATABASE customers", "sudo cat /etc/passwd", "cat ~/.ssh/id_rsa", "cat .env.local", "deploy to production"):
        result = engine.decide("risk_check", {"action": command})
        assert result["requires_human"] and result["risk"] in {"high", "destructive"}
    assert fake.calls == 0
    assert hard_risk("git status") is None
    assert hard_risk("cat .env.example") is None
    assert engine.decide("risk_check", {"action": "git status"})["reason_code"] == "deterministic_safe"


def test_decision_cache_and_failure():
    fake = FakeRuntime()
    engine = DecisionEngine(Config(), fake)
    state = {"current_phase": "testing", "language": "python"}
    assert engine.decide("test_decision", state)["decision"] == "targeted_test"
    assert engine.decide("test_decision", state)["decision"] == "targeted_test"
    assert fake.calls == 1 and engine.stats()["cache_hits"] == 1
    failed = DecisionEngine(Config(), FakeRuntime(fail=True))
    assert failed.decide("test_decision", state)["decision"] == "defer_to_agent"
    failed.runtime.fail = False
    assert failed.decide("test_decision", state)["decision"] == "targeted_test"
    with pytest.raises(ValueError):
        engine.decide("invalid", state)
    with pytest.raises(ValueError):
        engine.decide("test_decision", [])
    uncertain = DecisionEngine(Config(confidence_threshold=0.8), FakeRuntime(choice="safe", confidence=0.3))
    assert uncertain.decide("risk_check", {"action": "git push origin main"})["risk"] == "unknown"
    invalid = DecisionEngine(Config(), FakeRuntime(confidence=math.nan))
    assert invalid.decide("test_decision", state)["decision"] == "defer_to_agent"


def test_safe_task_and_risk_cache_without_secret_retention():
    route = FakeRuntime(choice="debugging")
    engine = DecisionEngine(Config(), route)
    task = {"request": "Fix the checkout bug", "cache_revision": "a" * 64}
    engine.decide("route_task", task)
    engine.decide("route_task", task)
    assert route.calls == 1
    engine.decide("route_task", {**task, "cache_revision": "b" * 64})
    assert route.calls == 2
    secret_task = {"request": "Fix login with token=abc123"}
    engine.decide("route_task", secret_task)
    engine.decide("route_task", secret_task)
    assert route.calls == 4
    assert all("token" not in key for key in engine.cache)

    risk = FakeRuntime(choice="low")
    engine = DecisionEngine(Config(), risk)
    action = {"action": "git push origin main", "cache_revision": "a" * 64}
    engine.decide("risk_check", action)
    engine.decide("risk_check", action)
    engine.decide("risk_check", {**action, "cache_revision": "b" * 64})
    assert risk.calls == 2


def test_corrupt_cache_entry_does_not_break_decision():
    fake = FakeRuntime()
    engine = DecisionEngine(Config(), fake)
    state = {"current_phase": "testing"}
    engine.decide("test_decision", state)
    key = next(iter(engine.cache))
    engine.cache[key] = (None, {})
    assert engine.decide("test_decision", state)["decision"] == "targeted_test"
    assert fake.calls == 2


def test_savings_only_count_explicit_avoided_call():
    engine = DecisionEngine(Config(), FakeRuntime())
    engine.decide("test_decision", {"current_phase": "testing", "language": "python"})
    assert engine.stats()["estimated_llm_calls_avoided"] == 0
    engine.decide("test_decision", {"current_phase": "testing", "language": "rust", "would_call_llm": True, "estimated_llm_tokens": 120})
    assert engine.stats()["estimated_llm_calls_avoided"] == 1
    assert engine.stats()["estimated_tokens_saved"] == 120


def test_stats_count_policy_requests_and_escalations():
    engine = DecisionEngine(Config(), FakeRuntime(choice="high"))
    engine.decide("risk_check", {"action": "git push origin main"})
    engine.decide("risk_check", {"action": "git push origin main"})
    engine.decide("test_decision", {"last_test_result": "failed"})
    stats = engine.stats()
    assert stats["decisions_by_policy"]["risk_check"] == 2
    assert stats["decisions_by_policy"]["test_decision"] == 1
    assert stats["escalations"] == 2


def test_route_confidence_is_not_used_as_calibrated_threshold():
    engine = DecisionEngine(Config(confidence_threshold=0.8), FakeRuntime(choice="debugging", confidence=0.2))
    result = engine.decide("route_task", {"request": "Fix the checkout bug"})
    assert result["decision"] == "debugging"
    assert result["reason_code"] == "confidence_uncalibrated"


def test_failed_test_routes_without_model():
    fake = FakeRuntime()
    engine = DecisionEngine(Config(), fake)
    assert engine.decide("test_decision", {"last_test_result": "failed"})["decision"] == "debug_failure"
    assert fake.calls == 0


def test_hooks_block_dangerous_commands_without_runtime():
    payload = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /tmp/example"}}
    codex = run("codex", "PreToolUse", payload)
    claude = run("claude", "PreToolUse", payload)
    opencode = run("opencode", "PreToolUse", payload)
    assert codex["hookSpecificOutput"]["permissionDecision"] == "deny"
    assert claude["hookSpecificOutput"]["permissionDecision"] == "ask"
    assert opencode["deny"] is True
    assert run("codex", "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "git status"}}) == {}
    assert run("opencode", "PreToolUse", {"tool_name": "read", "tool_input": {"filePath": "/repo/.env"}})["deny"]


def test_hooks_use_laya_at_test_and_commit_transitions():
    with patch("laya_agent.hooks._call", side_effect=lambda policy, state: {"decision": "targeted_test" if policy == "test_decision" else "self_review"}), patch("laya_agent.hooks.project_facts", return_value={"tests_available": True}), patch("laya_agent.hooks.git_facts", return_value={"changed_files": 2}):
        commit = run("codex", "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "git commit -m fix"}})
        assert "targeted_test" in commit["hookSpecificOutput"]["additionalContext"]
        passed = run("codex", "PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "pytest"}, "tool_response": {"exit_code": 0}})
        assert "self_review" in passed["hookSpecificOutput"]["additionalContext"]
        assert run("codex", "PostToolUse", {"tool_name": "Bash", "tool_input": {"command": "git status"}, "tool_response": {"exit_code": 0}}) == {}


def test_opencode_skips_precommit_hint_it_cannot_deliver():
    with patch("laya_agent.hooks._call") as decide:
        assert run("opencode", "PreToolUse", {"tool_name": "shell", "tool_input": {"command": "git commit -m fix"}}) == {}
    decide.assert_not_called()


def test_opencode_shell_risk_and_test_result():
    assert run("opencode", "PreToolUse", {"tool_name": "shell", "tool_input": {"command": "rm -rf /tmp/example"}})["deny"]
    with patch("laya_agent.hooks._call", return_value={"decision": "debug"}) as decide:
        result = run("opencode", "PostToolUse", {"tool_name": "shell", "tool_input": {"command": "pytest"}, "tool_response": {"output": "failed", "metadata": {"exit": 1}}})
    assert result["context"] == "Local decision: debug the failed test before proceeding."
    decide.assert_called_once_with("next_action", {"current_phase": "debugging", "last_test_result": "failed"})


def test_call_policy_skips_explicitly_unneeded_or_slow_low_value_work():
    assert not should_call_laya("route_task", {"request": "Fix bug", "would_call_llm": False})
    assert not should_call_laya("next_action", {"current_phase": "testing"}, latency_ms=600)
    assert should_call_laya("risk_check", {"action": "git push origin main"}, latency_ms=600)


def test_mcp_tools_registered():
    assert mcp.name == "cam-laya-mcp"
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert names == {"laya_status", "laya_decide", "laya_route_task", "laya_risk_check", "laya_next_action", "laya_test_decision", "laya_review_decision"}


def test_repeated_decisions_have_bounded_memory():
    engine = DecisionEngine(Config(), FakeRuntime())
    for changed_files in range(1100):
        engine.decide("test_decision", {"changed_files": changed_files})
    assert len(engine.cache) <= 1024
    assert len(engine.latencies) == 256


def test_config_idempotent(tmp_path):
    path = tmp_path / "config.toml"
    write_default(path)
    before = path.read_text()
    write_default(path)
    assert path.read_text() == before
    assert load_config(path).enabled
    path.write_text('enabled = "false"\n')
    with pytest.raises(ValueError):
        load_config(path)


def test_missing_runtime_setup_needs_approval(tmp_path, monkeypatch):
    from laya_agent import cli

    monkeypatch.setattr(cli, "environment", lambda: {"supported": True, "installed": False})
    monkeypatch.setattr(cli, "_isolated_exe", lambda: None)
    monkeypatch.setattr(cli, "ISOLATED_VENV", tmp_path / "venv")
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert cli.setup(SimpleNamespace(yes=False)) == 1


def test_repeat_setup_reuses_isolated_runtime(tmp_path, monkeypatch):
    from laya_agent import cli

    runtime = tmp_path / "venv"
    executable = runtime / "bin/cam-laya-mcp"
    monkeypatch.setattr(cli, "environment", lambda: {"supported": True, "installed": False})
    monkeypatch.setattr(cli, "ISOLATED_VENV", runtime)
    monkeypatch.setattr(cli, "_isolated_exe", lambda: executable)
    monkeypatch.setattr(cli, "write_default", lambda: None)
    monkeypatch.setattr(cli, "ADAPTERS", [])
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    assert cli.setup(SimpleNamespace(yes=False)) == 0
    assert [str(executable), "test"] in calls
    assert not any(args[0] == "uv" for args in calls)


def test_global_laya_does_not_hide_unusable_cli_runtime(tmp_path, monkeypatch):
    from laya_agent import cli

    monkeypatch.setattr(cli, "environment", lambda: {"supported": True, "installed": True})
    monkeypatch.setattr(cli, "_isolated_exe", lambda: None)
    monkeypatch.setattr(cli, "ISOLATED_VENV", tmp_path / "venv")
    monkeypatch.setattr(cli, "_exe", lambda: str(tmp_path / "missing-cam-laya-mcp"))
    monkeypatch.setattr(cli.sys, "stdin", SimpleNamespace(isatty=lambda: False))
    assert cli.setup(SimpleNamespace(yes=False)) == 1


def test_stats_survive_corrupt_saved_file(tmp_path, monkeypatch, capsys):
    from laya_agent import cli, daemon

    metrics = tmp_path / "stats.json"
    metrics.write_text("invalid json")
    monkeypatch.setattr(daemon, "METRICS", metrics)
    monkeypatch.setattr(cli, "request", lambda *a, **kw: (_ for _ in ()).throw(ConnectionError()))
    monkeypatch.setattr(sys, "argv", ["cam-laya-mcp", "stats"])
    with pytest.raises(SystemExit) as exit_info:
        cli.main()
    assert exit_info.value.code == 0
    assert '"laya_decisions": 0' in capsys.readouterr().out


def test_socket_request_rejects_oversized_state():
    from laya_agent.daemon import request

    with pytest.raises(ValueError, match="request too large"):
        request("decide", policy="route_task", state={"request": "x" * 9000})


def test_missing_runtime_never_authorizes_hard_risk():
    engine = DecisionEngine(Config(mandatory_safety=True), FakeRuntime(fail=True))
    assert engine.decide("risk_check", {"action": "git push --force origin main"})["requires_human"]
    unavailable = engine.decide("risk_check", {"action": "git push origin main"})
    assert unavailable["risk"] == "unknown" and unavailable["requires_human"]


@pytest.mark.parametrize("failure", [ConnectionError, TimeoutError])
def test_mandatory_hook_and_mcp_fail_closed_when_daemon_fails(failure):
    from laya_agent.mcp_server import laya_risk_check

    with patch("laya_agent.hooks.request", side_effect=failure), patch("laya_agent.hooks.load_config", return_value=Config(mandatory_safety=True)), patch("laya_agent.policy.load_config", return_value=Config(mandatory_safety=True)), patch("laya_agent.hooks.git_facts", return_value={}):
        result = run("codex", "PreToolUse", {"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"
    with patch("laya_agent.mcp_server.request", side_effect=failure), patch("laya_agent.policy.load_config", return_value=Config(mandatory_safety=True)):
        assert laya_risk_check("git push origin main")["requires_human"]


def test_environment_rejects_non_apple_silicon(monkeypatch):
    import laya_agent.runtime as runtime
    monkeypatch.setattr(runtime.sys, "platform", "linux")
    assert runtime.environment()["supported"] is False


def test_project_metadata_cache_invalidates_on_manifest_change(tmp_path):
    manifest = tmp_path / "package.json"
    manifest.write_text('{"scripts": {"test": "vitest"}, "dependencies": {"next": "15"}}')
    assert project_facts(tmp_path) == {"language": "javascript", "framework": "nextjs", "tests_available": True}
    (tmp_path / "tsconfig.json").write_text("{}")
    assert project_facts(tmp_path)["language"] == "typescript"


def test_git_revision_changes_when_same_file_count_changes(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    file = tmp_path / "feature.py"
    file.write_text("a")
    os.utime(file, ns=(1, 1))
    first = git_facts(tmp_path)
    file.write_text("b")
    os.utime(file, ns=(2, 2))
    second = git_facts(tmp_path)
    assert first["changed_files"] == second["changed_files"] == 1
    assert first["cache_revision"] != second["cache_revision"]
    (tmp_path / "space name.py").write_text("c")
    assert git_facts(tmp_path)["changed_files"] == 2
