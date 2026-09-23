from __future__ import annotations

import json
from types import SimpleNamespace

import laya_agent.integrations as integrations


def test_hook_install_idempotent_and_preserves_other_hooks(tmp_path):
    path = tmp_path / "hooks.json"
    existing = {"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "my-policy"}]}]}, "other": 7}
    path.write_text(json.dumps(existing))
    added = integrations._add_hooks(path, ["PreToolUse", "SessionStart"], "/tmp/laya-agent", "codex")
    first = json.loads(path.read_text())
    integrations._add_hooks(path, ["PreToolUse", "SessionStart"], "/tmp/laya-agent", "codex")
    second = json.loads(path.read_text())
    assert first == second
    assert second["other"] == 7
    integrations._remove_hooks(path, added)
    after = json.loads(path.read_text())
    assert after["hooks"]["PreToolUse"][0]["hooks"][0]["command"] == "my-policy"


def test_opencode_plugin_contract():
    plugin = integrations.PLUGIN
    assert "session.created" in plugin
    assert "tool.execute.before" in plugin
    assert "tool.execute.after" in plugin
    assert "throw new Error" in plugin


def test_opencode_install_uninstall_preserves_other_config(tmp_path, monkeypatch):
    config = tmp_path / "opencode.jsonc"
    config.write_text('{ // user comment\n "theme": "dark", "mcp": {"other": {"type": "local", "command": ["other"]}}, }')
    monkeypatch.setattr(integrations, "DEFAULT_OPENCODE_DIR", tmp_path)
    monkeypatch.setattr(integrations, "OPENCODE_CONFIG", tmp_path / "opencode.json")
    monkeypatch.setattr(integrations, "OPENCODE_PLUGIN", tmp_path / "plugins/laya-agent.js")
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    adapter = integrations.OpenCodeAdapter()
    adapter.install("/tmp/laya-agent")
    first = integrations._read_json(config)
    adapter.install("/tmp/laya-agent")
    assert integrations._read_json(config) == first
    assert first["theme"] == "dark" and "other" in first["mcp"]
    assert adapter.validate()["installed"]
    adapter.uninstall()
    after = integrations._read_json(config)
    assert after["mcp"] == {"other": {"type": "local", "command": ["other"]}}
    assert "user comment" in (tmp_path / "opencode.jsonc.laya-agent.bak").read_text() or after["theme"] == "dark"


def test_codex_adapter_owns_only_its_entries(tmp_path, monkeypatch):
    hooks = tmp_path / "hooks.json"
    hooks.write_text(json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "user-start"}]}]}}))
    monkeypatch.setattr(integrations, "CODEX_HOOKS", hooks)
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    existing = {"mcp": False}
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ["codex", "mcp", "get"]:
            return SimpleNamespace(returncode=0 if existing["mcp"] else 1, stdout="/tmp/laya-agent mcp" if existing["mcp"] else "")
        if args[:3] == ("codex", "mcp", "add"):
            existing["mcp"] = True
        if args[:3] == ("codex", "mcp", "remove"):
            existing["mcp"] = False
        return SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)
    adapter = integrations.CodexAdapter()
    adapter.install("/tmp/laya-agent")
    adapter.install("/tmp/laya-agent")
    assert len([x for x in calls if x[:3] == ("codex", "mcp", "add")]) == 1
    adapter.uninstall()
    assert not existing["mcp"]
    assert integrations._read_json(hooks)["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "user-start"


def test_opencode_active_and_default_config(tmp_path, monkeypatch):
    old = tmp_path / "old"
    new = tmp_path / "new"
    (old / "plugins").mkdir(parents=True)
    (old / "opencode.json").write_text('{"mcp":{"laya-agent":{"type":"local","command":["/tmp/laya-agent","mcp"]}}}')
    (old / "plugins/laya-agent.js").write_text("owned")
    monkeypatch.setattr(integrations, "DEFAULT_OPENCODE_DIR", old)
    monkeypatch.setattr(integrations, "OPENCODE_CONFIG", new / "opencode.json")
    monkeypatch.setattr(integrations, "OPENCODE_PLUGIN", new / "plugins/laya-agent.js")
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    integrations._save_manifest({"opencode_mcp": True, "opencode_plugin": True})
    integrations.OpenCodeAdapter().install("/tmp/laya-agent")
    assert "laya-agent" in integrations._read_json(old / "opencode.json")["mcp"]
    assert (old / "plugins/laya-agent.js").exists()
    assert "laya-agent" in integrations._read_json(new / "opencode.json")["mcp"]
    integrations.OpenCodeAdapter().uninstall()
    assert "laya-agent" not in integrations._read_json(old / "opencode.json")["mcp"]
    assert "laya-agent" not in integrations._read_json(new / "opencode.json")["mcp"]


def test_claude_uninstall_only_owned_user_server(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    settings.write_text('{"hooks":{"SessionStart":[{"hooks":[{"type":"command","command":"user-start"}]}]}}')
    user = tmp_path / "claude.json"
    user.write_text('{"mcpServers":{"laya-agent":{"command":"/tmp/laya-agent","args":["mcp"]},"other":{"command":"other"}},"theme":"dark"}')
    monkeypatch.setattr(integrations, "CLAUDE_SETTINGS", settings)
    monkeypatch.setattr(integrations, "CLAUDE_USER_CONFIG", user)
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    integrations._save_manifest({"claude_mcp": True, "claude_mcp_executable": "/tmp/laya-agent"})
    integrations.ClaudeAdapter().uninstall()
    data = integrations._read_json(user)
    assert data["mcpServers"] == {"other": {"command": "other"}}
    assert data["theme"] == "dark"
    assert integrations._read_json(settings)["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "user-start"
