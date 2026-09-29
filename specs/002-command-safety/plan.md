# Milestone 2 plan

## Design

1. Keep the existing shared `hard_risk` function as the safety boundary used by policy, hooks, and fallback.
2. Use Python `shlex` to split common shell commands into executed segments. Apply command-specific checks to executable tokens instead of matching every keyword in raw text.
3. Retain text checks for SQL destruction, secret paths, credential manipulation, prompt injection, and production deployment. Fail closed on malformed shell syntax.
4. Extend Git and shell rules for observed gaps. Document the static-analysis limit without adding a parser dependency.

## Verification

Use one parameterized regression set through `hard_risk`, `DecisionEngine`, and the Codex hook. Check benign quoted examples separately. Run `uv run pytest -q` and `git diff --check` after the change.

## Result

Implemented in `src/laya_agent/policy.py`, tested in `tests/test_core.py`, and documented in `README.md`. Verification: 85 tests passed; whitespace check passed. Milestone 1's failed productivity gate remains unchanged.
