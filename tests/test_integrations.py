from __future__ import annotations

import json
import shutil
import subprocess
from types import SimpleNamespace

import pytest

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


def test_owned_hook_path_upgrade_and_validation(tmp_path, monkeypatch):
    hooks = tmp_path / "hooks.json"
    monkeypatch.setattr(integrations, "CODEX_HOOKS", hooks)
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    monkeypatch.setattr(integrations.CodexAdapter, "detect", lambda self: True)
    monkeypatch.setattr(integrations.subprocess, "run", lambda *a, **kw: SimpleNamespace(returncode=0))
    owned = {}
    events = ["SessionStart", "PreToolUse"]
    integrations._install_hooks(hooks, events, "/tmp/old", "codex", owned, "codex_hooks")
    integrations._save_manifest(owned)
    integrations._install_hooks(hooks, events, "/tmp/cam-laya-mcp", "codex", owned, "codex_hooks")
    integrations._save_manifest(owned)
    commands = [h["command"] for groups in integrations._read_json(hooks)["hooks"].values() for g in groups for h in g["hooks"]]
    assert len(commands) == 2
    assert all("/tmp/cam-laya-mcp" in command for command in commands)
    assert integrations.CodexAdapter().validate()["hooks"]


def test_opencode_plugin_contract():
    plugin = integrations.PLUGIN
    assert "session.created" in plugin
    assert "tool.execute.before" in plugin
    assert "tool.execute.after" in plugin
    assert "throw new Error" in plugin


def test_opencode_post_tool_decision_reaches_agent(tmp_path):
    if not shutil.which("node"):
        pytest.skip("Node.js unavailable")
    plugin = integrations.PLUGIN.replace(
        'import { execFileSync } from "node:child_process";',
        'let calls = 0; const execFileSync = (_bin, args) => (calls++, JSON.stringify(args[2] === "PreToolUse" '
        '? {deny: true, reason: "unsafe"} : {context: "Local decision: debug."}));',
    ).replace("__EXECUTABLE__", '"/tmp/cam-laya-mcp"')
    script = tmp_path / "plugin.mjs"
    script.write_text(
        plugin + '\nconst hooks = await LayaAgent();\n'
        'const output = {output: "test failed", title: "test", metadata: {}};\n'
        'await hooks["tool.execute.after"]({tool: "bash", args: {command: "pytest"}}, output);\n'
        'if (!output.output.includes("Local decision: debug.")) process.exit(1);\n'
        'await hooks["tool.execute.after"]({tool: "shell", args: {command: "git status"}}, output);\n'
        'if (calls !== 1) process.exit(4);\n'
        'try { await hooks["tool.execute.before"]({tool: "shell"}, {args: {command: "rm -rf /tmp/x"}}); process.exit(2); }\n'
        'catch (error) { if (!String(error).includes("unsafe")) process.exit(3); }\n'
    )
    subprocess.run(["node", str(script)], check=True, capture_output=True, text=True)


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
    assert "user comment" in config.read_text()
    assert after["theme"] == "dark"


def test_owned_opencode_path_upgrade_and_comment_preservation(tmp_path, monkeypatch):
    config = tmp_path / "opencode.jsonc"
    config.write_text('{ // keep this note\n "theme": "https://example.test", "mcp": {} }')
    monkeypatch.setattr(integrations, "DEFAULT_OPENCODE_DIR", tmp_path)
    monkeypatch.setattr(integrations, "OPENCODE_CONFIG", tmp_path / "opencode.json")
    monkeypatch.setattr(integrations, "OPENCODE_PLUGIN", tmp_path / "plugins/laya-agent.js")
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    adapter = integrations.OpenCodeAdapter()
    adapter.install("/tmp/old")
    adapter.install("/tmp/new")
    assert integrations._read_json(config)["mcp"]["cam-laya-mcp"]["command"] == ["/tmp/new", "mcp"]
    assert 'const bin = "/tmp/new"' in (tmp_path / "plugins/laya-agent.js").read_text()
    assert "// keep this note" in config.read_text()
    assert config.read_text().count("// keep this note") == 1
    adapter.uninstall()
    assert "// keep this note" in config.read_text()


def test_opencode_upgrade_refuses_edited_plugin_before_config_write(tmp_path, monkeypatch):
    config = tmp_path / "opencode.json"
    monkeypatch.setattr(integrations, "DEFAULT_OPENCODE_DIR", tmp_path)
    monkeypatch.setattr(integrations, "OPENCODE_CONFIG", config)
    monkeypatch.setattr(integrations, "OPENCODE_PLUGIN", tmp_path / "plugins/laya-agent.js")
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    adapter = integrations.OpenCodeAdapter()
    adapter.install("/tmp/old")
    plugin = tmp_path / "plugins/laya-agent.js"
    plugin.write_text("user edit")
    before = config.read_text()
    with pytest.raises(ValueError, match="plugin was edited"):
        adapter.install("/tmp/new")
    assert config.read_text() == before


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
            return SimpleNamespace(returncode=0 if existing["mcp"] else 1, stdout="command: /tmp/laya-agent\nargs: mcp" if existing["mcp"] else "")
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
    assert ("codex", "mcp", "add", "cam-laya-mcp", "--", "/tmp/laya-agent", "mcp") in calls
    adapter.uninstall()
    assert not existing["mcp"]
    assert integrations._read_json(hooks)["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "user-start"


def test_codex_migrates_owned_legacy_mcp(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "CODEX_HOOKS", tmp_path / "hooks.json")
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    integrations._save_manifest({"codex_mcp": True})
    names = {"laya-agent"}

    def fake_run(args, **kwargs):
        if args[:3] == ("codex", "mcp", "add"):
            names.add(args[3])
        elif args[:3] == ("codex", "mcp", "remove"):
            names.remove(args[3])
        return SimpleNamespace(returncode=0 if args[3] in names else 1, stdout="command: /tmp/laya-agent\nargs: mcp")

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)
    adapter = integrations.CodexAdapter()
    adapter.install("/tmp/laya-agent")
    adapter.install("/tmp/laya-agent")
    assert names == {"cam-laya-mcp"}
    adapter.uninstall()
    assert not names


def test_codex_upgrades_owned_mcp_path(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "CODEX_HOOKS", tmp_path / "hooks.json")
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    integrations._save_manifest({"codex_mcp": True, "codex_mcp_name": "cam-laya-mcp", "codex_mcp_executable": "/tmp/old"})
    current = {"executable": "/tmp/old"}

    def fake_run(args, **kwargs):
        if args[:3] == ("codex", "mcp", "remove"):
            current["executable"] = ""
        if args[:3] == ("codex", "mcp", "add"):
            current["executable"] = args[5]
        return SimpleNamespace(returncode=0, stdout=f"command: {current['executable']}\nargs: mcp")

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)
    integrations.CodexAdapter().install("/tmp/new")
    assert current["executable"] == "/tmp/new"
    assert integrations._manifest()["codex_mcp_executable"] == "/tmp/new"


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
    assert "cam-laya-mcp" in integrations._read_json(old / "opencode.json")["mcp"]
    assert "laya-agent" not in integrations._read_json(old / "opencode.json")["mcp"]
    assert (old / "plugins/laya-agent.js").exists()
    assert "cam-laya-mcp" in integrations._read_json(new / "opencode.json")["mcp"]
    integrations.OpenCodeAdapter().uninstall()
    assert "cam-laya-mcp" not in integrations._read_json(old / "opencode.json")["mcp"]
    assert "cam-laya-mcp" not in integrations._read_json(new / "opencode.json")["mcp"]


def test_opencode_discovers_live_config_source(tmp_path, monkeypatch):
    active = tmp_path / "active"
    live = tmp_path / "live/opencode.json"
    monkeypatch.setattr(integrations, "OPENCODE_DIR", active)
    monkeypatch.setattr(integrations, "OPENCODE_CONFIG", active / "opencode.json")
    monkeypatch.setattr(integrations, "OPENCODE_PLUGIN", active / "plugins/laya-agent.js")
    monkeypatch.setattr(integrations, "DEFAULT_OPENCODE_DIR", active)
    monkeypatch.setattr(integrations.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(integrations.shutil, "which", lambda name: "/tmp/opencode")
    monkeypatch.setattr(integrations.subprocess, "run", lambda *a, **kw: SimpleNamespace(stdout=json.dumps([{"type": "document", "path": str(live)}])))
    assert (live, live.parent / "plugins/laya-agent.js") in integrations._opencode_targets()


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


def test_claude_install_is_idempotent_and_preserves_other_servers(tmp_path, monkeypatch):
    settings = tmp_path / "settings.json"
    user = tmp_path / "claude.json"
    user.write_text('{"mcpServers":{"other":{"command":"other"}}}')
    monkeypatch.setattr(integrations, "CLAUDE_SETTINGS", settings)
    monkeypatch.setattr(integrations, "CLAUDE_USER_CONFIG", user)
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    names = set()
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        if args[:3] == ("claude", "mcp", "add"):
            names.add("cam-laya-mcp")
        return SimpleNamespace(returncode=0 if "cam-laya-mcp" in names else 1, stdout="/tmp/laya-agent mcp")

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)
    adapter = integrations.ClaudeAdapter()
    adapter.install("/tmp/laya-agent")
    adapter.install("/tmp/laya-agent")
    assert sum(args[:3] == ("claude", "mcp", "add") for args in calls) == 1
    data = integrations._read_json(user)
    data["mcpServers"]["cam-laya-mcp"] = {"command": "/tmp/laya-agent", "args": ["mcp"]}
    integrations._write_json(user, data)
    adapter.uninstall()
    assert integrations._read_json(user)["mcpServers"] == {"other": {"command": "other"}}


def test_uninstall_preserves_repointed_codex_and_opencode_entries(tmp_path, monkeypatch):
    monkeypatch.setattr(integrations, "MANIFEST", tmp_path / "installed.json")
    monkeypatch.setattr(integrations, "CODEX_HOOKS", tmp_path / "hooks.json")
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout="/tmp/user-tool mcp")

    monkeypatch.setattr(integrations.subprocess, "run", fake_run)
    integrations._save_manifest({"codex_mcp": True, "codex_mcp_name": "cam-laya-mcp", "codex_mcp_executable": "/tmp/laya-agent"})
    integrations.CodexAdapter().uninstall()
    assert not any(args[:3] == ("codex", "mcp", "remove") for args in calls)

    config = tmp_path / "opencode.json"
    plugin = tmp_path / "plugins/laya-agent.js"
    monkeypatch.setattr(integrations, "DEFAULT_OPENCODE_DIR", tmp_path)
    monkeypatch.setattr(integrations, "OPENCODE_CONFIG", config)
    monkeypatch.setattr(integrations, "OPENCODE_PLUGIN", plugin)
    integrations.OpenCodeAdapter().install("/tmp/laya-agent")
    data = integrations._read_json(config)
    data["mcp"]["cam-laya-mcp"]["command"] = ["/tmp/user-tool", "mcp"]
    integrations._write_json(config, data)
    plugin.write_text("user plugin edit")
    integrations.OpenCodeAdapter().uninstall()
    assert integrations._read_json(config)["mcp"]["cam-laya-mcp"]["command"] == ["/tmp/user-tool", "mcp"]
    assert plugin.read_text() == "user plugin edit"
