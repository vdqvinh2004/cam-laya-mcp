# Milestone 7 plan

## Design

Docs-and-verification only. No behavior change:

1. Update `docs/release-readiness.md` current-verification section: 85 tests (was 59), Milestone 2 static shell-scan outcome, fresh read-only `doctor` snapshot (darwin-arm64, macOS 27.0, isolated Python 3.12.14, Laya-MLX 0.2.0, MLX 0.32.2; live Codex hooks/MCP absent; OpenCode MCP disconnected with unowned plugin present; Claude absent). Keep the Fail / no-saving language for productivity and cost.
2. Update `specs/README.md` milestone table with the Milestone 7 row.
3. Inspect the `uv build` outputs (`dist/cam_laya_mcp-0.1.0.tar.gz`, `dist/cam_laya_mcp-0.1.0-py3-none-any.whl`): list contents, confirm the wheel payload is the `laya_agent` package plus metadata (sdist is the full source tree).
4. Record this verification evidence in the Result section below; do not touch live client homes.

## Verification

- `uv run pytest -q` → 85 passed.
- `git diff --check` → clean.
- `uv run python benchmarks/evaluate_codex.py --self-check` → passed.
- `uv build` → sdist + wheel (rebuilt during this milestone).
- `uv run cam-laya-mcp doctor` (read-only, no setup/uninstall) → snapshot recorded above.

## Result

2026-09-28 run, no live client config changed:

- `uv run pytest -q` → 85 passed.
- `git diff --check` → clean.
- `uv run python benchmarks/evaluate_codex.py --self-check` → passed.
- `uv build` → `dist/cam_laya_mcp-0.1.0.tar.gz` + `dist/cam_laya_mcp-0.1.0-py3-none-any.whl`; wheel payload is the ten `laya_agent` modules plus `dist-info` metadata.
- `uv run cam-laya-mcp doctor` (read-only) → darwin-arm64, macOS 27.0, isolated Python 3.12.14, Laya-MLX 0.2.0, MLX 0.32.2, model cache present; live Codex hooks/MCP absent, OpenCode MCP disconnected with unowned plugin present, Claude absent.

Docs updated in `docs/release-readiness.md` and `specs/README.md`. Milestone 1's failed productivity gate remains unchanged.
