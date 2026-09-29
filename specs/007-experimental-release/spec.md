# Milestone 7: Experimental release hardening

**Status:** Implemented.

## Goal

Ship v0.1.0 as an honest experimental release: deterministic command-safety rules on by default, model decisions and post-test guidance opt-in, and no productivity or cost claim. Close the documentation gaps left by Milestone 2 without mutating any live client configuration.

## User scenarios

1. A maintainer runs the standard verification on this Mac and gets a current, reproducible result: 85 unit tests, whitespace check, evaluation self-check, inspectable build artifacts, and read-only `doctor` output.
2. A new user reads the README and release audit and understands the tool is experimental, which integrations are verified only in disposable profiles, and that live Codex/OpenCode rollout remains unverified here.
3. A user with an existing OpenCode plugin or Codex profile runs setup without losing unowned entries; where verification is impossible on this Mac (Claude Code absent, no live hook trust), the docs say so.

## Acceptance

- `docs/release-readiness.md` reports the Milestone 2 test count (85), the fresh read-only `doctor` result (live Codex hooks/MCP absent, OpenCode MCP disconnected, Claude absent), and keeps the failed productivity gate language unchanged.
- `uv build` artifacts exist from the working tree and their contents are inspected (wheel payload is the `laya_agent` package plus metadata; sdist is the full source tree).
- `uv run pytest -q`, `git diff --check`, and `uv run python benchmarks/evaluate_codex.py --self-check` pass; evidence is recorded in the plan result.
- No live client config is created, modified, or trusted as part of this milestone; `doctor` is run read-only.
- No new dependency, model call, hook event, or MCP tool is added.

## Non-goals

- No productivity, token, or cost improvement claim.
- No live Codex hook-trust review, live OpenCode takeover, or Claude Code session.
- No change to deterministic rules, policy defaults, or evaluation methodology.
