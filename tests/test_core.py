from __future__ import annotations

import asyncio

import pytest

from laya_agent.config import Config, load_config, write_default
from laya_agent.context import compact, fingerprint, project_facts
from laya_agent.hooks import run
from laya_agent.mcp_server import mcp
from laya_agent.policy import DecisionEngine, hard_risk


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


def test_hard_rules_override_model():
    fake = FakeRuntime(choice="safe")
    engine = DecisionEngine(Config(), fake)
    for command in ("rm -rf /", "git push --force origin main", "terraform destroy", "DROP DATABASE customers", "sudo cat /etc/passwd", "cat ~/.ssh/id_rsa", "deploy to production"):
        result = engine.decide("risk_check", {"action": command})
        assert result["requires_human"] and result["risk"] in {"high", "destructive"}
    assert fake.calls == 0
    assert hard_risk("git status") is None
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
    with pytest.raises(ValueError):
        engine.decide("invalid", state)
    uncertain = DecisionEngine(Config(confidence_threshold=0.8), FakeRuntime(choice="safe", confidence=0.3))
    assert uncertain.decide("risk_check", {"action": "git push origin main"})["risk"] == "unknown"


def test_savings_only_count_explicit_avoided_call():
    engine = DecisionEngine(Config(), FakeRuntime())
    engine.decide("test_decision", {"current_phase": "testing", "language": "python"})
    assert engine.stats()["estimated_llm_calls_avoided"] == 0
    engine.decide("test_decision", {"current_phase": "testing", "language": "rust", "would_call_llm": True, "estimated_llm_tokens": 120})
    assert engine.stats()["estimated_llm_calls_avoided"] == 1
    assert engine.stats()["estimated_tokens_saved"] == 120


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


def test_mcp_tools_registered():
    names = {tool.name for tool in asyncio.run(mcp.list_tools())}
    assert names == {"laya_status", "laya_decide", "laya_route_task", "laya_risk_check", "laya_next_action", "laya_test_decision", "laya_review_decision"}


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


def test_missing_runtime_never_authorizes_hard_risk():
    engine = DecisionEngine(Config(mandatory_safety=True), FakeRuntime(fail=True))
    assert engine.decide("risk_check", {"action": "git push --force origin main"})["requires_human"]
    unavailable = engine.decide("risk_check", {"action": "git push origin main"})
    assert unavailable["risk"] == "unknown" and unavailable["requires_human"]


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
