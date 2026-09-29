# Milestone 8 validation guide

These steps use disposable client homes. They must not change the user's live Codex, Claude Code, or OpenCode configuration.

## Guard-only clean room

1. On macOS and Linux with Python 3.11+, install the package without the MLX extra. Use temporary `HOME`, `XDG_CONFIG_HOME`, `XDG_STATE_HOME`, `CODEX_HOME`, and OpenCode config paths where each client supports them. Keep Laya-MLX, its checkpoint, and `uv` absent from this test profile.
2. Run `cam-laya-mcp setup --guard-only` while it is the candidate mode; after the gate passes, rerun with plain `setup`. Confirm only owned PreToolUse guard entries appear and no model files, daemon process, or advisory MCP entry appears.
3. Send `git status` and a locked destructive command through each available client hook. Confirm safe pass and the client-specific deny or review response with a stable reason.
4. Rerun setup, then uninstall. Compare unrelated client entries and JSONC comments byte-for-byte before and after; confirm no unowned entry changed.

## Compatibility and optional model

1. In a separate disposable profile, start with an existing `enabled = true` config and owned MCP entry. Rerun setup; confirm model preference and healthy owned entries survive. Simulate missing runtime and confirm setup reports the issue without silently downloading or disabling the model.
2. On supported Apple Silicon, approve `setup --with-model`, run the existing model smoke check and MCP stdio roundtrip, then test `enable` and `disable`. Inject a model-install failure; guard hooks must still work.
3. Run read-only `doctor`. Treat configured hooks, trusted hooks, and observed live hook events as different states. Do not claim a client verified if its binary or trust review is unavailable.

## Release checks

Run `uv run pytest -q`, the isolated MCP roundtrip, `uv build`, `git diff --check`, the locked plus holdout command corpora, 100-process safe-hook latency samples on the reference Mac, and a paired benign coding screen. Report all counts and failures. Apply the gate in [plan.md](plan.md) before making guard-only setup the default or changing the release claim.
