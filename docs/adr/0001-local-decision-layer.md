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
- [MCP specification: stdio transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports)
- [Official OpenAI Docs: Codex MCP](https://developers.openai.com/codex/mcp)
- [Official OpenAI Docs: Codex hooks](https://developers.openai.com/codex/hooks)
- [Official Claude Code hooks](https://code.claude.com/docs/en/hooks)
- [Official Claude Code MCP](https://code.claude.com/docs/en/mcp)
- [Official OpenCode plugins](https://opencode.ai/docs/plugins/)
- [Official OpenCode MCP](https://opencode.ai/docs/mcp-servers/)
- [OpenCode shell tool implementation](https://github.com/anomalyco/opencode/blob/dev/packages/opencode/src/tool/shell.ts) (uses `shell` and reports `metadata.exit`)

## Consequences

- Hooks defer ordinary decisions on model failure. Configured mandatory risk checks fail closed, and hard rules still block dangerous commands.
- Local process and model lifetime are shared by MCP and hooks; no public HTTP service.
- User configuration is merged and backed up. OpenCode's active override directory, default user directory, and live config source discovered through `opencode debug config` are configured when different. JSONC comments remain in the active file, grouped above the rewritten JSON object.
- Codex user hooks require a one-time `/hooks` trust action required by Codex itself.
- OpenCode's plugin can append post-test guidance to a tool result. It cannot show a nonblocking precommit hint through the documented tool hook, so that decision is skipped there.
- Token savings cannot be inferred from decision counts. The statistics command reports zero estimated savings until an actual client accounting method is implemented.

## Milestone 2 API review

The current [Laya-MLX 0.2.0 Python API](https://github.com/mizorewww/laya-mlx#python-api) supports `choice`, `score`, and `noul`; its Router and presets target multiple checkpoints and other application workflows. The five coding policies need categorical choices, so `choice` is the shortest direct fit. `score` would add rubric mapping without improving a current policy, and `noul` would duplicate existing deterministic binary guards. Router preload would keep extra checkpoints resident; the default English coding workflow uses one checkpoint. A user can set another compatible checkpoint ID. Add Router or another decision type when a measured multilingual or ordered-score use case requires it.
