# Milestone 5 validation guide

These are acceptance steps for the planned implementation; the full coding-task runner is not implemented yet.

## Prerequisites

Apple Silicon with the installed isolated Laya-MLX runtime, working `codex exec`, and the current repository checkout. Record the model, Codex version, checkpoint, commit, and published pricing date before a run. Keep temporary Codex homes and coding checkouts isolated from the user's normal state.

## Fast checks

1. Run `uv run pytest -q` after the timeout and routing changes. The focused checks must prove no resend after a socket response timeout, safe fallback, cache invalidation, one automatic hint for unchanged state, and recovery after a slow model sample.
2. Run `uv run python benchmarks/evaluate_codex.py --self-check` after changing event parsing. A missing or malformed token field must surface as an error or null value, never as invented savings.
3. Run the diagnostic no-Laya/hooks-only/MCP-only/both profiles on the five existing prompts. Inspect cold and warm stages and confirm every run has an end-to-end time including startup. Use these runs only for overhead attribution.

## Coding-task comparison

1. Run the selected integration and no-Laya condition on the same six-or-more task definitions, five paired trials each, with fresh checkouts and counterbalanced order. Use the new runner profile documented by its implementation task.
2. For every trial, inspect executable check result, patch rubric, tool calls, first useful response, total time, input/cached/output tokens, and local decision stages. Failed or incomplete trials remain in the result set.
3. Generate the paired report with per-task medians and 95% paired bootstrap intervals. Confirm the gate in `plan.md` and update `docs/codex-efficacy-baseline.md` with the before/after result, negative findings included.

Stop the comparison if a condition violates hard safety or repeatedly fails task checks. The final report must name any stopped cohort and why.
