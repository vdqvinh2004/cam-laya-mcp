from __future__ import annotations

import hashlib
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
MCP_NAME = "cam-laya-mcp"
LEGACY_MCP_NAME = "laya-agent"


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
    targets = [active] if active == default else [active, default]
    if OPENCODE_CONFIG == OPENCODE_DIR / "opencode.json" and shutil.which("opencode"):
        try:
            listed = subprocess.run(["opencode", "debug", "config"], capture_output=True, text=True, timeout=10, check=True)
            for source in json.loads(listed.stdout):
                if not isinstance(source, dict):
                    continue
                path = Path(source.get("path", ""))
                if path.name in {"opencode.json", "opencode.jsonc"} and path.is_relative_to(Path.home()) and not path.is_relative_to(Path.cwd()):
                    target = (path, path.parent / "plugins/laya-agent.js")
                    if target not in targets:
                        targets.append(target)
        except (OSError, ValueError, subprocess.SubprocessError, TypeError):
            pass
    return targets


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    comments = ""
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".laya-agent.bak"))
        if path.suffix == ".jsonc":
            raw = path.read_text()
            found = []
            i = 0
            quote = ""
            while i < len(raw):
                char = raw[i]
                if quote:
                    if char == "\\":
                        i += 2
                        continue
                    if char == quote:
                        quote = ""
                elif char in "\"'":
                    quote = char
                elif raw.startswith("//", i):
                    end = raw.find("\n", i)
                    end = len(raw) if end < 0 else end
                    found.append(raw[i:end])
                    i = end
                    continue
                elif raw.startswith("/*", i):
                    end = raw.find("*/", i + 2)
                    end = len(raw) if end < 0 else end + 2
                    found.append(raw[i:end])
                    i = end
                    continue
                i += 1
            comments = "\n".join(found) + "\n" if found else ""
    path.write_text(comments + json.dumps(data, indent=2) + "\n")


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


def _install_hooks(path: Path, events: list[str], executable: str, client: str, owned: dict, key: str) -> None:
    wanted = {f"{shlex.quote(executable)} hook {client} {event}" for event in events}
    stale = [item for item in owned.get(key, []) if item not in wanted]
    if stale:
        _remove_hooks(path, stale)
    added = _add_hooks(path, events, executable, client)
    owned[key] = sorted((set(owned.get(key, [])) - set(stale)) | set(added))


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
        return {"mcp": True, "hooks": ["SessionStart", "PreToolUse", "PostToolUse"], "automatic": True, "config": str(CODEX_HOOKS)}

    def install(self, executable: str) -> None:
        owned = _manifest()
        legacy_owned = owned.get("codex_mcp") and owned.get("codex_mcp_name", LEGACY_MCP_NAME) == LEGACY_MCP_NAME
        listed = subprocess.run(["codex", "mcp", "get", MCP_NAME], capture_output=True, text=True)
        if listed.returncode:
            _run("codex", "mcp", "add", MCP_NAME, "--", executable, "mcp")
            owned["codex_mcp"] = True
        elif executable not in listed.stdout:
            previous = owned.get("codex_mcp_executable")
            if not owned.get("codex_mcp") or not previous or f"command: {previous}" not in listed.stdout:
                raise ValueError(f"Codex MCP name {MCP_NAME} already points elsewhere")
            _run("codex", "mcp", "remove", MCP_NAME)
            _run("codex", "mcp", "add", MCP_NAME, "--", executable, "mcp")
        if legacy_owned:
            legacy = subprocess.run(["codex", "mcp", "get", LEGACY_MCP_NAME], capture_output=True, text=True)
            if legacy.returncode == 0 and ("/laya-agent" in legacy.stdout or "/cam-laya-mcp" in legacy.stdout):
                _run("codex", "mcp", "remove", LEGACY_MCP_NAME)
        if owned.get("codex_mcp"):
            owned["codex_mcp_name"] = MCP_NAME
            owned["codex_mcp_executable"] = executable
        _install_hooks(CODEX_HOOKS, self.capabilities()["hooks"], executable, "codex", owned, "codex_hooks")
        _save_manifest(owned)

    def uninstall(self) -> None:
        owned = _manifest()
        if commands := owned.pop("codex_hooks", []):
            _remove_hooks(CODEX_HOOKS, commands)
        name = owned.pop("codex_mcp_name", LEGACY_MCP_NAME)
        executable = owned.pop("codex_mcp_executable", None)
        if owned.pop("codex_mcp", False) and self.detect():
            listed = subprocess.run(["codex", "mcp", "get", name], capture_output=True, text=True)
            if listed.returncode == 0 and executable and any(line.strip() == f"command: {executable}" for line in listed.stdout.splitlines()):
                _run("codex", "mcp", "remove", name)
        _save_manifest(owned)

    def validate(self) -> dict:
        data = _read_json(CODEX_HOOKS)
        commands = {h.get("command") for groups in data.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])}
        hooks = bool(commands & set(_manifest().get("codex_hooks", [])))
        mcp = self.detect() and subprocess.run(["codex", "mcp", "get", MCP_NAME], capture_output=True).returncode == 0
        return {"installed": bool(hooks and mcp), "hooks": hooks, "mcp": mcp}


class ClaudeAdapter(ClientAdapter):
    def __init__(self):
        super().__init__("claude")

    def capabilities(self) -> dict:
        return {"mcp": True, "hooks": ["SessionStart", "PreToolUse", "PostToolUse"], "automatic": True, "config": str(CLAUDE_SETTINGS)}

    def install(self, executable: str) -> None:
        owned = _manifest()
        legacy_owned = owned.get("claude_mcp") and owned.get("claude_mcp_name", LEGACY_MCP_NAME) == LEGACY_MCP_NAME
        listed = subprocess.run(["claude", "mcp", "get", MCP_NAME], capture_output=True, text=True)
        if listed.returncode:
            _run("claude", "mcp", "add", "--scope", "user", MCP_NAME, "--", executable, "mcp")
            owned["claude_mcp"] = True
            owned["claude_mcp_executable"] = executable
        elif executable not in listed.stdout:
            previous = owned.get("claude_mcp_executable")
            if not owned.get("claude_mcp") or not previous or previous not in listed.stdout:
                raise ValueError(f"Claude MCP name {MCP_NAME} already points elsewhere")
            _run("claude", "mcp", "remove", MCP_NAME)
            _run("claude", "mcp", "add", "--scope", "user", MCP_NAME, "--", executable, "mcp")
            owned["claude_mcp_executable"] = executable
        if legacy_owned:
            legacy = subprocess.run(["claude", "mcp", "get", LEGACY_MCP_NAME], capture_output=True, text=True)
            if legacy.returncode == 0 and owned.get("claude_mcp_executable") and owned["claude_mcp_executable"] in legacy.stdout:
                _run("claude", "mcp", "remove", LEGACY_MCP_NAME)
        if owned.get("claude_mcp"):
            owned["claude_mcp_name"] = MCP_NAME
        _install_hooks(CLAUDE_SETTINGS, self.capabilities()["hooks"], executable, "claude", owned, "claude_hooks")
        _save_manifest(owned)

    def uninstall(self) -> None:
        owned = _manifest()
        if commands := owned.pop("claude_hooks", []):
            _remove_hooks(CLAUDE_SETTINGS, commands)
        name = owned.pop("claude_mcp_name", LEGACY_MCP_NAME)
        if owned.pop("claude_mcp", False):
            data = _read_json(CLAUDE_USER_CONFIG)
            server = data.get("mcpServers", {}).get(name, {})
            if server.get("command") == owned.get("claude_mcp_executable"):
                data["mcpServers"].pop(name, None)
                _write_json(CLAUDE_USER_CONFIG, data)
        owned.pop("claude_mcp_executable", None)
        _save_manifest(owned)

    def validate(self) -> dict:
        data = _read_json(CLAUDE_SETTINGS)
        commands = {h.get("command") for groups in data.get("hooks", {}).values() for g in groups for h in g.get("hooks", [])}
        hooks = bool(commands & set(_manifest().get("claude_hooks", [])))
        mcp = self.detect() and subprocess.run(["claude", "mcp", "get", MCP_NAME], capture_output=True).returncode == 0
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
        plugin_hashes = owned.get("opencode_plugin_hashes", {})
        if owned.get("opencode_mcp"):
            configs.add(owned.get("opencode_config_path", str(DEFAULT_OPENCODE_DIR / "opencode.json")))
        if owned.get("opencode_plugin"):
            plugins.add(owned.get("opencode_plugin_path", str(DEFAULT_OPENCODE_DIR / "plugins/laya-agent.js")))
        for config, plugin in _opencode_targets():
            rendered = PLUGIN.replace("__EXECUTABLE__", json.dumps(executable))
            plugin_owned = str(plugin) in plugins
            recorded = plugin_hashes.get(str(plugin))
            if plugin.exists() and plugin.read_text() != rendered:
                if not plugin_owned or (recorded and recorded != hashlib.sha256(plugin.read_bytes()).hexdigest()):
                    raise ValueError(f"OpenCode plugin was edited or is unowned: {plugin}")
            data = _read_json(config)
            current = data.get("mcp", {}).get(MCP_NAME)
            previous = owned.get("opencode_mcp_executable")
            if current and current.get("command") != [executable, "mcp"]:
                if str(config) not in configs or current.get("command") != [previous, "mcp"]:
                    raise ValueError(f"OpenCode MCP name {MCP_NAME} already points elsewhere in {config}")
            changed = False
            if current and current.get("command") != [executable, "mcp"]:
                current["command"] = [executable, "mcp"]
                changed = True
            elif not current:
                data.setdefault("mcp", {})[MCP_NAME] = {"type": "local", "command": [executable, "mcp"], "enabled": True}
                changed = True
                configs.add(str(config))
            if data.get("mcp", {}).get(LEGACY_MCP_NAME, {}).get("command") == [executable, "mcp"]:
                data["mcp"].pop(LEGACY_MCP_NAME)
                changed = True
            if changed:
                _write_json(config, data)
            if plugin.exists() and plugin_owned and plugin.read_text() != rendered:
                if recorded:
                    plugin.write_text(rendered)
            elif not plugin.exists():
                plugin.parent.mkdir(parents=True, exist_ok=True)
                plugin.write_text(rendered)
                plugins.add(str(plugin))
            if str(plugin) in plugins and plugin.read_text() == rendered:
                plugin_hashes[str(plugin)] = hashlib.sha256(plugin.read_bytes()).hexdigest()
        owned["opencode_config_paths"] = sorted(configs)
        owned["opencode_plugin_paths"] = sorted(plugins)
        owned["opencode_plugin_hashes"] = plugin_hashes
        owned["opencode_mcp_executable"] = executable
        owned["opencode_mcp_name"] = MCP_NAME
        for key in ("opencode_mcp", "opencode_plugin", "opencode_config_path", "opencode_plugin_path"):
            owned.pop(key, None)
        _save_manifest(owned)

    def uninstall(self) -> None:
        owned = _manifest()
        name = owned.pop("opencode_mcp_name", LEGACY_MCP_NAME)
        executable = owned.pop("opencode_mcp_executable", None)
        configs = owned.pop("opencode_config_paths", [])
        plugins = owned.pop("opencode_plugin_paths", [])
        plugin_hashes = owned.pop("opencode_plugin_hashes", {})
        if owned.pop("opencode_mcp", False):
            configs.append(owned.get("opencode_config_path", str(DEFAULT_OPENCODE_DIR / "opencode.json")))
        if owned.pop("opencode_plugin", False):
            plugins.append(owned.get("opencode_plugin_path", str(DEFAULT_OPENCODE_DIR / "plugins/laya-agent.js")))
        for path in set(configs):
            config = Path(path)
            data = _read_json(config)
            if executable and data.get("mcp", {}).get(name, {}).get("command") == [executable, "mcp"]:
                data["mcp"].pop(name)
                _write_json(config, data)
        for path in set(plugins):
            plugin = Path(path)
            if plugin.exists() and plugin_hashes.get(path) == hashlib.sha256(plugin.read_bytes()).hexdigest():
                plugin.unlink()
        owned.pop("opencode_config_path", None)
        owned.pop("opencode_plugin_path", None)
        _save_manifest(owned)

    def validate(self) -> dict:
        targets = _opencode_targets()
        mcp = all(MCP_NAME in _read_json(config).get("mcp", {}) for config, _ in targets)
        plugin = all(path.exists() for _, path in targets)
        result = {"installed": mcp and plugin, "mcp": mcp, "plugin": plugin}
        if self.detect() and targets[0][0].parent == OPENCODE_DIR:
            listed = subprocess.run(["opencode", "mcp", "list"], capture_output=True, text=True, timeout=30)
            result["client_connected"] = listed.returncode == 0 and MCP_NAME in listed.stdout and "connected" in listed.stdout
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
    if (!["shell", "bash", "Bash", "exec_command", "read", "Read", "read_file"].includes(input.tool)) return;
    const result = decide("PreToolUse", { tool_name: input.tool, tool_input: output.args });
    if (result.deny) throw new Error(result.reason || "Action requires human approval");
  },
  "tool.execute.after": async (input, output) => {
    if (!["shell", "bash", "Bash", "exec_command"].includes(input.tool)) return;
    const command = input.args?.command || input.args?.cmd || "";
    if (!["pytest", "npm test", "cargo test", "go test", "vitest"].some(word => command.includes(word))) return;
    const result = decide("PostToolUse", { tool_name: input.tool, tool_input: input.args, tool_response: output });
    if (result.context) output.output += "\\n" + result.context;
  },
});
'''


ADAPTERS = [CodexAdapter(), ClaudeAdapter(), OpenCodeAdapter()]
