# Native hook contract

## Guard-only events

Register `PreToolUse` for recognized shell and file-read tools. Do not register `SessionStart`, `UserPromptSubmit`, or `PostToolUse` for a new guard-only profile. Preserve an existing user's explicit post-test guidance preference.

For a recognized safe action, return the client's empty/no-op response without a model or daemon request. For a covered risk, include a stable reason code without logging the raw command or path:

| Client | Risk response | Limit |
| --- | --- | --- |
| Codex | PreToolUse `deny` with reason | Documented hook `ask` support is absent; user may take approved action manually. |
| Claude Code | PreToolUse `ask` with reason | Claim live support only after a real Claude session verifies it. |
| OpenCode | Plugin `deny` with reason | Plugin stops the tool; user may act manually. |

Unknown tools follow the existing client workflow. A static rule can cover specified destructive forms, secret paths, and malformed shell text; this contract does not promise to inspect external scripts or dynamically generated commands.

## Optional model events

When the user explicitly enables the model, retain current typed MCP tools and supported hook behavior. Deterministic hard-risk decisions always run first. Post-test guidance stays off unless the existing preference explicitly enables it.
