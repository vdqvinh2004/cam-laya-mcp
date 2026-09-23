# v0.1.0 release readiness — 2026-09-23

**Status: release candidate, not yet a verified three-client release.** The remaining validation is a live Claude Code session; its binary is not installed on this Mac. Codex and OpenCode are installed and connected.

| Requirement group | Status | Evidence |
| --- | --- | --- |
| Local runtime and platform | Pass on this Mac | Apple Silicon/macOS detected; Laya-MLX 0.2.0 and MLX 0.32.2 load locally; real checkpoint inference passes. PyTorch Laya and cloud inference are not runtime dependencies. |
| Setup and lifecycle | Pass on this Mac | Approved isolated runtime exists; repeat `setup` exits successfully without changing owned client configuration; session hooks start or reuse one local daemon. |
| MCP and decisions | Pass | Seven compact tools; real stdio roundtrip; hard risk rules, bounded context, cache, and model-failure fallback covered by tests. |
| Codex | Pass, with native trust step | MCP and hooks validate; hook activity is recorded. Codex requires one-time `/hooks` trust review. |
| OpenCode | Pass at plugin boundary | MCP connected; current `shell` tool and `metadata.exit` handled; Node test verifies risk denial and post-test guidance reaches the tool output. A full coding session was not run. |
| Claude Code | **Live test pending** | Adapter install, ownership, and hook tests pass with fixtures. Claude Code is absent, so an actual session and MCP connection were not verified. |
| CLI, privacy, metrics | Pass | `doctor`, model `test`, benchmark, stats, and owned uninstall paths tested. Logs exclude prompts and commands. Token savings remain zero until a caller provides a defensible avoided-call estimate. |
| Package | Pass | Wheel and source distribution build; metadata includes README, Apache-2.0 license, repository URLs, and optional Laya-MLX dependency. |

## Current validation

- 44 tests pass; Ruff passes; `git diff --check` passes.
- Local benchmark: model load 2117.71 ms; warm decisions 23.24–62.13 ms over five samples; MCP tool roundtrip 3.54 ms. These are measurements on one machine, not product guarantees.
- Repeat setup preserved hashes of the owned Codex hooks, OpenCode config/plugin, and install manifest.

## Before a full release

1. Run setup and a real prompt/tool cycle in Claude Code on an Apple Silicon Mac, then confirm MCP and hook results.
2. Review and commit the current working tree; create the first release tag from the tested commit.

Known client limits: OpenCode has no documented user-prompt hook or nonblocking precommit hint channel. Its automatic path covers session start, risk checks, and post-test guidance. MCP registration alone never guarantees visible agent tool calls. No actual token saving has been demonstrated yet, so release notes must not claim one.
