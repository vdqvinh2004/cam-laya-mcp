from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import json5

from .config import CONFIG_DIR

MANIFEST = CONFIG_DIR / "installed.json"
CODEX_HOOKS = Path.home() / ".codex/hooks.json"
CLAUDE_SETTINGS = Path.home() / ".claude/settings.json"
CLAUDE_USER_CONFIG = Path.home() / ".claude.json"
DEFAULT_OPENCODE_DIR = Path.home() / ".config/opencode"
OPENCODE_DIR = Path(os.environ.get("OPENCODE_CONFIG_DIR", DEFAULT_OPENCODE_DIR))
OPENCODE_CONFIG = OPENCODE_DIR / "opencode.json"
OPENCODE_PLUGIN = OPENCODE_DIR / "plugins/laya-agent.js"


def _manifest() -> dict:
    try:
        return json.loads(MANIFEST.read_text())
    except FileNotFoundError:
        return {}


def _save_manifest(data: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n")
    MANIFEST.chmod(0o600)


def _read_json(path: Path) -> dict:
    try:
        raw = path.read_text()
    except FileNotFoundError:
        return {}
    value = json5.loads(raw) if path.suffix == ".jsonc" else json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"Expected JSON object: {path}")
    return value


def _opencode_config(path: Path = OPENCODE_CONFIG) -> Path:
    jsonc = path.with_suffix(".jsonc")
    return jsonc if jsonc.exists() and not path.exists() else path


def _opencode_targets() -> list[tuple[Path, Path]]:
    active = (_opencode_config(OPENCODE_CONFIG), OPENCODE_PLUGIN)
    default = (_opencode_config(DEFAULT_OPENCODE_DIR / "opencode.json"), DEFAULT_OPENCODE_DIR / "plugins/laya-agent.js")
    return [active] if active == default else [active, default]


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".laya-agent.bak"))
    path.write_text(json.dumps(data, indent=2) + "\n")


def _add_hooks(path: Path, events: list[str], command: str, client: str) -> list[str]:
    data = _read_json(path)
    hooks = data.setdefault("hooks", {})
    added = []
    changed = False
    for event in events:
        groups = hooks.setdefault(event, [])
        hook_command = f"{shlex.quote(command)} hook {client} {event}"
        wanted = {"hooks": [{"type": "command", "command": hook_command, "timeout": 5}]}
        if event == "PreToolUse":
            wanted["matcher"] = "Bash|bash|exec_command|Read|read|read_file"
        existing = next((group for group in groups if any(h.get("command") == hook_command for h in group.get("hooks", []))), None)
        if existing is None:
            groups.append(wanted)
            added.append(hook_command)
            changed = True
        elif existing.get("hooks") == wanted["hooks"] and existing.get("matcher") != wanted.get("matcher"):
            if "matcher" in wanted:
                existing["matcher"] = wanted["matcher"]
            else:
                existing.pop("matcher", None)
            changed = True
    if changed:
        _write_json(path, data)
    return added


def _remove_hooks(path: Path, commands: list[str]) -> None:
    if not path.exists():
        return
    data = _read_json(path)
    for event, groups in list(data.get("hooks", {}).items()):
        remaining = []
        for group in groups:
            handlers = [h for h in group.get("hooks", []) if h.get("command") not in commands]
            if handlers:
                remaining.append({**group, "hooks": handlers})
        if remaining:
            data["hooks"][event] = remaining
        else:
            del data["hooks"][event]
    _write_json(path, data)


def _run(*args: str) -> None:
    subprocess.run(args, check=True, capture_output=True, text=True, timeout=30)


@dataclass
class ClientAdapter:
    name: str

    def detect(self) -> bool:
        return shutil.which(self.name) is not None

    def capabilities(self) -> dict:
        raise NotImplementedError

    def install(self, executable: str) -> None:
        raise NotImplementedError

    def uninstall(self) -> None:
        raise NotImplementedError

    def validate(self) -> dict:
        raise NotImplementedError


class CodexAdapter(ClientAdapter):
    def __init__(self):
        super().__init__("codex")

    def capabilities(self) -> dict:
        return {"mcp": True, "hooks": ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"], "automatic": True, "config": str(CODEX_HOOKS)}

    def install(self, executable: str) -> None:
        owned = _manifest()
        listed = subprocess.run(["codex", "mcp", "get", "laya-agent"], capture_output=True, text=True)
        if listed.returncode:
            _run("codex", "mcp", "add", "laya-agent", "--", executable, "mcp")
            owned["codex_mcp"] = True
        elif executable not in listed.stdout:
            raise ValueError("Codex MCP name laya-agent already points elsewhere")
        added = _add_hooks(CODEX_HOOKS, self.capabilities()["hooks"], executable, "codex")
        owned["codex_hooks"] = sorted(set(owned.get("codex_hooks", []) + added))
        _save_manifest(owned)

    def uninstall(self) -> None:
        owned = _manifest()
        if commands := owned.pop("codex_hooks", []):
            _remove_hooks(CODEX_HOOKS, commands)
        if owned.pop("codex_mcp", False) and self.detect():
            _run("codex", "mcp", "remove", "laya-agent")
        _save_manifest(owned)

    def validate(self) -> dict:
        data = _read_json(CODEX_HOOKS)
        hooks = any("laya-agent" in str(g) for groups in data.get("hooks", {}).values() for g in groups)
        mcp = self.detect() and subprocess.run(["codex", "mcp", "get", "laya-agent"], capture_output=True).returncode == 0
        return {"installed": bool(hooks and mcp), "hooks": hooks, "mcp": mcp}


class ClaudeAdapter(ClientAdapter):
    def __init__(self):
        super().__init__("claude")

    def capabilities(self) -> dict:
        return {"mcp": True, "hooks": ["SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse"], "automatic": True, "config": str(CLAUDE_SETTINGS)}

    def install(self, executable: str) -> None:
        owned = _manifest()
        listed = subprocess.run(["claude", "mcp", "get", "laya-agent"], capture_output=True, text=True)
        if listed.returncode:
            _run("claude", "mcp", "add", "--scope", "user", "laya-agent", "--", executable, "mcp")
            owned["claude_mcp"] = True
            owned["claude_mcp_executable"] = executable
        elif executable not in listed.stdout:
            raise ValueError("Claude MCP name laya-agent already points elsewhere")
        added = _add_hooks(CLAUDE_SETTINGS, self.capabilities()["hooks"], executable, "claude")
        owned["claude_hooks"] = sorted(set(owned.get("claude_hooks", []) + added))
        _save_manifest(owned)

    def uninstall(self) -> None:
        owned = _manifest()
        if commands := owned.pop("claude_hooks", []):
            _remove_hooks(CLAUDE_SETTINGS, commands)
        if owned.pop("claude_mcp", False):
            data = _read_json(CLAUDE_USER_CONFIG)
            server = data.get("mcpServers", {}).get("laya-agent", {})
            if server.get("command") == owned.get("claude_mcp_executable"):
                data["mcpServers"].pop("laya-agent", None)
                _write_json(CLAUDE_USER_CONFIG, data)
        owned.pop("claude_mcp_executable", None)
        _save_manifest(owned)

    def validate(self) -> dict:
        data = _read_json(CLAUDE_SETTINGS)
        hooks = any("laya-agent" in str(g) for groups in data.get("hooks", {}).values() for g in groups)
        mcp = self.detect() and subprocess.run(["claude", "mcp", "get", "laya-agent"], capture_output=True).returncode == 0
        return {"installed": bool(hooks and mcp), "hooks": hooks, "mcp": mcp}


class OpenCodeAdapter(ClientAdapter):
    def __init__(self):
        super().__init__("opencode")

    def capabilities(self) -> dict:
        return {"mcp": True, "plugins": ["session.created", "tool.execute.before", "tool.execute.after"], "automatic": True, "config": [str(config) for config, _ in _opencode_targets()]}

    def install(self, executable: str) -> None:
        owned = _manifest()
        configs = set(owned.get("opencode_config_paths", []))
        plugins = set(owned.get("opencode_plugin_paths", []))
        if owned.get("opencode_mcp"):
            configs.add(owned.get("opencode_config_path", str(DEFAULT_OPENCODE_DIR / "opencode.json")))
        if owned.get("opencode_plugin"):
            plugins.add(owned.get("opencode_plugin_path", str(DEFAULT_OPENCODE_DIR / "plugins/laya-agent.js")))
        for config, plugin in _opencode_targets():
            data = _read_json(config)
            if "laya-agent" in data.get("mcp", {}) and data["mcp"]["laya-agent"].get("command") != [executable, "mcp"]:
                raise ValueError(f"OpenCode MCP name laya-agent already points elsewhere in {config}")
            if "laya-agent" not in data.get("mcp", {}):
                data.setdefault("mcp", {})["laya-agent"] = {"type": "local", "command": [executable, "mcp"], "enabled": True}
                _write_json(config, data)
                configs.add(str(config))
            if not plugin.exists():
                plugin.parent.mkdir(parents=True, exist_ok=True)
                plugin.write_text(PLUGIN.replace("__EXECUTABLE__", json.dumps(executable)))
                plugins.add(str(plugin))
        owned["opencode_config_paths"] = sorted(configs)
        owned["opencode_plugin_paths"] = sorted(plugins)
        for key in ("opencode_mcp", "opencode_plugin", "opencode_config_path", "opencode_plugin_path"):
            owned.pop(key, None)
        _save_manifest(owned)

    def uninstall(self) -> None:
        owned = _manifest()
        configs = owned.pop("opencode_config_paths", [])
        plugins = owned.pop("opencode_plugin_paths", [])
        if owned.pop("opencode_mcp", False):
            configs.append(owned.get("opencode_config_path", str(DEFAULT_OPENCODE_DIR / "opencode.json")))
        if owned.pop("opencode_plugin", False):
            plugins.append(owned.get("opencode_plugin_path", str(DEFAULT_OPENCODE_DIR / "plugins/laya-agent.js")))
        for path in set(configs):
            config = Path(path)
            data = _read_json(config)
            data.get("mcp", {}).pop("laya-agent", None)
            _write_json(config, data)
        for path in set(plugins):
            Path(path).unlink(missing_ok=True)
        owned.pop("opencode_config_path", None)
        owned.pop("opencode_plugin_path", None)
        _save_manifest(owned)

    def validate(self) -> dict:
        targets = _opencode_targets()
        mcp = all("laya-agent" in _read_json(config).get("mcp", {}) for config, _ in targets)
        plugin = all(path.exists() for _, path in targets)
        result = {"installed": mcp and plugin, "mcp": mcp, "plugin": plugin}
        if self.detect() and targets[0][0].parent == OPENCODE_DIR:
            listed = subprocess.run(["opencode", "mcp", "list"], capture_output=True, text=True, timeout=30)
            result["client_connected"] = listed.returncode == 0 and "laya-agent" in listed.stdout and "connected" in listed.stdout
            result["installed"] = result["installed"] and result["client_connected"]
        return result


PLUGIN = '''import { execFileSync } from "node:child_process";
const bin = __EXECUTABLE__;
function decide(event, payload) {
  try {
    return JSON.parse(execFileSync(bin, ["hook", "opencode", event], {
      input: JSON.stringify(payload), encoding: "utf8", timeout: 5000,
      stdio: ["pipe", "pipe", "ignore"],
    }) || "{}");
  } catch { return {}; }
}
export const LayaAgent = async () => ({
  event: async ({ event }) => {
    if (event.type === "session.created") decide("SessionStart", event);
  },
  "tool.execute.before": async (input, output) => {
    const result = decide("PreToolUse", { tool_name: input.tool, tool_input: output.args });
    if (result.deny) throw new Error(result.reason || "Action requires human approval");
  },
  "tool.execute.after": async (input, output) => {
    decide("PostToolUse", { tool_name: input.tool, tool_input: input.args, tool_response: output });
  },
});
'''


ADAPTERS = [CodexAdapter(), ClaudeAdapter(), OpenCodeAdapter()]
