# Milestone 9 Validation Guide

This is the execution guide for the later implementation. No candidate hook or benchmark profile exists yet.

## Prerequisites

Finish Milestone 8 hosted CI and review the release diff. Use a disposable `CODEX_HOME` and repository snapshots, a pinned Codex version/model, Git, Python 3.11+, and the two task repositories pinned in the future Milestone 9 corpus. Do not use the user's active client config for the experiment.

## Gate order

1. **G0 delivery**: In the disposable profile, register one `UserPromptSubmit` probe, submit one prompt, and verify the official JSON `additionalContext` reaches the agent. Record version and trust state; remove the probe. Stop if it does not arrive.
2. **G1 pilot**: Run four discovery and two bypass pilot prompts. Require four top-three targets, zero bypass hints, and zero unsafe paths. Allow one documented adjustment, then freeze code.
3. **G2 safety/latency**: Run `uv run pytest -q`, `uv run python benchmarks/evaluate_guard.py --check-gate --latency-samples 100`, 100 prompt-hook lookup samples, and one disposable live safe-pass/destructive-deny trial. Require context p95 ≤250 ms and the Milestone 8 guard gates to pass.
4. **G1 main and G3–G4 paired coding**: Open the untouched main set (eight discovery, four bypass); first require at least seven top-three targets and zero bypass hints, with no further tuning. Run `benchmarks/evaluate_codex.py` with isolated `hooks_pre` (guard-only) and `context` profiles for four pairs per task, then use `benchmarks/summarize_codex.py` with task-cluster analysis. Check all 48 pairs, quality, time, tokens, bypass overhead, and documented exclusions.
5. **G5 cost**: Attach attributable provider billing if available; otherwise report token use and labeled price estimates without a billed-cost claim.
6. **Closeout**: Run MCP stdio roundtrip, `uv build`, `git diff --check`, and read-only `cam-laya-mcp doctor`. Update [release readiness](../../docs/release-readiness.md) with pass/fail results and supported-client limits.

Every gate must be recorded even when later gates are skipped. A failed G0 or G1 stops coding-study spend; a failed G3 or G4 keeps the context feature disabled and blocks an efficiency claim.
