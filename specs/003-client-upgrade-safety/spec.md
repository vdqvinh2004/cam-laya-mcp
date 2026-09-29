# Milestone 3: Client upgrade safety

**Status:** Completed before the current command-safety milestone.

## Goal

Rerunning setup or moving the CLI executable must repair owned integrations without duplicating hooks, overwriting unrelated client settings, or losing OpenCode JSONC comments.

## Acceptance

- Reuse a healthy isolated Laya-MLX runtime on repeat setup.
- Replace stale owned Codex and Claude hook commands without adding duplicates.
- Upgrade owned OpenCode MCP and plugin paths; leave unowned entries untouched.
- Preserve comments in active OpenCode JSONC configuration through setup and uninstall.

Implementation and boundary checks live in `src/laya_agent/integrations.py`, `src/laya_agent/cli.py`, and `tests/test_integrations.py`. Client rollout status remains in [release readiness](../../docs/release-readiness.md).
