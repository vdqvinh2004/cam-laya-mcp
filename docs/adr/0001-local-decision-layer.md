# ADR 0001: Local typed decisions beside coding LLMs

Status: accepted, 2026-09-23. Upstream Laya-MLX revision inspected: `0a85951` (0.2.0).

## Decision

Use `laya_mlx.load("aac6fef/laya-mlx", dtype="float16")`, then `predict(state, {id: {"type": "choice", "instructions": ..., "criteria": [...]}})`. One local Unix socket process holds the model. Native client hooks/plugins invoke a small CLI bridge; an MCP stdio server exposes seven tools and talks to the same process. Laya is a routing hint, not authorization. Hard rules block configured dangerous actions before inference.

The Router supports multiple checkpoints, but this product uses one English checkpoint by default to avoid duplicate model loads. A user may set another current Laya-MLX compatible model ID in config.

## Capability matrix

| Client | MCP | Hooks | Plugins / skills | Lifecycle events used | Automatic invocation | Config location |
| --- | --- | --- | --- | --- | --- | --- |
| Codex | stdio | native hooks | plugins and skills available | SessionStart, UserPromptSubmit, PreToolUse, PostToolUse | hooks; first run needs trust review | `~/.codex/hooks.json`, MCP in `~/.codex/config.toml` via CLI |
| Claude Code | stdio | native hooks | plugins and skills available | SessionStart, UserPromptSubmit, PreToolUse, PostToolUse | hooks | `~/.claude/settings.json`, user MCP via CLI |
| OpenCode | local MCP | plugin events | plugins available | session.created, tool.execute.before/after | local JS plugin | `OPENCODE_CONFIG_DIR` when set, otherwise `~/.config/opencode/opencode.json[c]` and `plugins/` |
| Generic MCP client | client-dependent | none assumed | client-dependent | none assumed | explicit agent choice only | client-specific |

MCP exposes tools but does not guarantee the agent calls them. OpenCode's documented plugin events do not include a user-prompt event, so the OpenCode adapter routes session and tool transitions only.

## Sources inspected

- [Laya-MLX README and Python API](https://github.com/mizorewww/laya-mlx/tree/0a85951)
- [MCP specification: stdio transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports)
- [Official OpenAI Docs: Codex MCP](https://developers.openai.com/codex/mcp)
- [Official OpenAI Docs: Codex hooks](https://developers.openai.com/codex/hooks)
- [Official Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Official Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Official OpenCode plugins](https://opencode.ai/docs/plugins/)
- [Official OpenCode MCP](https://opencode.ai/docs/mcp-servers/)

## Consequences

- Hooks can fail open for model failures while hard rules still block dangerous commands.
- Local process and model lifetime are shared by MCP and hooks; no public HTTP service.
- User configuration is merged and backed up. OpenCode's active override directory and default user directory are both configured when different. JSONC is parsed and rewritten as valid JSONC-compatible JSON, so comments remain in its `.laya-agent.bak` backup.
- Codex user hooks require a one-time `/hooks` trust action required by Codex itself.
- Token savings cannot be inferred from decision counts. The statistics command reports zero estimated savings until an actual client accounting method is implemented.
