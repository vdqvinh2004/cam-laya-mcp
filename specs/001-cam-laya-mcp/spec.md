# Milestone 1: Local decision layer

**Status:** Foundation complete. Do not claim a productivity or cost benefit.

## Goal

Give coding agents a local Laya-MLX choice service for short workflow decisions while the coding agent keeps repository reasoning and code generation.

## Delivered scope

- Python package with setup, doctor, benchmark, stats, disable, and uninstall commands.
- Shared local daemon, seven stdio MCP tools, and Codex, Claude Code, and OpenCode integrations.
- Deterministic hard-risk rules, compact local model input, bounded decision cache, failure fallback, and integration ownership checks.
- Early production hardening, including mandatory-safety fallback and bounded local logging.

## Outcome

Model decisions remain opt-in. Post-test guidance remains off by default. Later evaluation and retrieval work has its own [Milestone 4](../004-codex-efficacy/spec.md), [Milestone 5](../005-measurable-efficiency/spec.md), and [Milestone 6](../006-agent-context-retrieval/spec.md) folders. See [release gates](../../docs/release-readiness.md).

Milestone 2 owns later command-safety work; Milestone 3 owns client upgrade safety.
