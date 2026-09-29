# Tasks: Offline Safety Default

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), and [contracts](contracts/cli.md)  
**Status**: Implemented; local release gates passed. Hosted CI awaits a pushed commit.

## Phase 1: Setup and baseline

**Purpose**: Freeze evidence before changing default behavior.

- [x] T001 Build a labeled locked set of at least 100 covered destructive and 100 benign actions plus separate holdouts in `benchmarks/guard_cases.json`; include shell quoting, wrappers, substitutions, pipes, Git discard, secret paths, and malformed input.
- [x] T002 [P] Add a repeatable whole-process hook latency and corpus runner to `benchmarks/evaluate_guard.py`; report median/p95, case IDs, pass/fail, and model/daemon starts without raw command logging.
- [x] T003 [P] Add an Ubuntu Python 3.11+ guard-only test job in `.github/workflows/test.yml`; keep MLX tests confined to a supported Mac.

## Phase 2: Foundational checks

**Purpose**: Lock current safety and ownership contracts before modifying setup.

- [x] T004 Add failing guard-only setup and owned-entry preservation checks for Codex, Claude Code, and OpenCode in `tests/test_integrations.py`; assert no MCP or extra hook event in a new guard profile.
- [x] T005 [P] Add failing safe-pass, destructive-deny, secret-read, and no-daemon-start hook checks in `tests/test_core.py`; include each client's response contract.

## Phase 3: User Story 1 — useful setup without a model (P1) MVP

**Goal**: A new Mac or Linux user can install working safety hooks with no MLX runtime.

**Independent test**: Run `setup --guard-only` in a clean no-MLX/no-`uv` profile, then exercise safe and risky hook actions; no model files or MCP entry appear.

- [x] T006 [US1] Add `setup --guard-only` in `src/laya_agent/cli.py`, moving model platform, install, and smoke work out of the candidate guard path while keeping partial client failure visible.
- [x] T007 [US1] Make adapter installation choose owned guard-only entries without advisory MCP registration in `src/laya_agent/integrations.py`; retain idempotence and unowned-entry refusal.
- [x] T008 [US1] Keep routine `PreToolUse` safety checks free of daemon/model requests and remove unused default events in `src/laya_agent/hooks.py` and `src/laya_agent/integrations.py`.
- [x] T009 [US1] Run the clean-room guard-only sequence from `specs/008-offline-safety-default/quickstart.md` on the reference Mac and an Ubuntu 24.04 container matching the CI job; record observed setup and hook results in `specs/008-offline-safety-default/plan.md`. Hosted CI awaits a pushed commit.

## Phase 4: User Story 2 — explicit model experiment and safe upgrade (P1)

**Goal**: Existing model users keep their preference and owned tools; new users opt in separately.

**Independent test**: Upgrade a model-enabled disposable profile, simulate a missing runtime, then try `setup --with-model` and legacy `setup --yes`; guard remains active and unrelated settings remain byte-for-byte intact.

- [x] T010 [US2] Add failing upgrade, missing-runtime, legacy `--yes`, model-install failure, and owned/unowned uninstall cases in `tests/test_core.py` and `tests/test_integrations.py`.
- [x] T011 [US2] Add explicit `setup --with-model`, preserve legacy `setup --yes`, and keep guard active on model failure in `src/laya_agent/cli.py`.
- [x] T012 [US2] Preserve `enabled = true` and existing config paths while registering owned MCP only for healthy model mode in `src/laya_agent/config.py` and `src/laya_agent/integrations.py`.
- [x] T013 [US2] Make `enable` verify runtime readiness without changing config on failure; keep `disable` model-only and uninstall manifest-owned in `src/laya_agent/cli.py`.
- [x] T014 [US2] Verify the existing typed MCP roundtrip and Laya smoke on supported Apple Silicon in `tests/test_mcp_roundtrip.py` and `specs/008-offline-safety-default/plan.md`.

## Phase 5: User Story 3 — clear status and low overhead (P2)

**Goal**: Users see guard and model readiness separately; routine actions stay fast and quiet.

**Independent test**: `doctor` distinguishes configured from observed hooks and optional model readiness; 100 routine hook processes meet the latency gate without a daemon start.

- [x] T015 [US3] Add diagnostic-state and compatibility checks for configured, verified, absent, and model-unavailable clients in `tests/test_core.py` and `tests/test_integrations.py`.
- [x] T016 [US3] Report guard/client verification separately from model/runtime/MCP readiness while retaining existing diagnostic keys in `src/laya_agent/cli.py`.
- [x] T017 [US3] Defer setup, integration, daemon, MCP, and benchmark imports on the `hook` path in `src/laya_agent/cli.py` and `src/laya_agent/hooks.py`; measure the whole process using `benchmarks/evaluate_guard.py`.
- [x] T018 [US3] Run at least one disposable live-client safe-pass and dangerous-block trial (Codex first, OpenCode if available) and record trust or unavailable-client limits in `docs/release-readiness.md`; if no client executes a hook, fail SC-004.

## Phase 6: Release gate and documentation

- [x] T019 Run locked and holdout corpora with `benchmarks/evaluate_guard.py`; fix observed rule failures in `src/laya_agent/policy.py` and focused `tests/test_core.py` cases while retaining the static-scan limit.
- [x] T020 Run at least six benign coding tasks with three matched pairs each using `benchmarks/evaluate_codex.py`; record task checks, time, tokens, and hook calls in `docs/release-readiness.md` without a savings claim.
- [x] T021 Apply SC-001 through SC-006: if passed, make guard-only the default `setup` behavior in `src/laya_agent/cli.py` and update `README.md` plus `specs/README.md`; if failed, leave the existing default and record failed gates in those docs.
- [x] T022 Run full `uv run pytest -q`, MCP roundtrip, `uv build`, `git diff --check`, and read-only `doctor`; record exact results and supported-client limits in `specs/008-offline-safety-default/plan.md` and `docs/release-readiness.md`.

## Dependencies and execution order

T001–T003 establish corpus, benchmark, and Linux coverage. T004–T005 lock behavior before T006–T008. US1 reaches an independently usable guard-only candidate at T009. US2 starts after T007 so ownership mode exists; US3 can begin after T008 and run alongside US2. T019–T020 need the candidate and diagnostic work. T021 is the release decision after those measurements; T022 verifies the exact chosen default.

## Parallel opportunities

T002 and T003 touch separate files and can run alongside corpus authoring. T005 can run alongside T004. After the guard candidate exists, model migration work (US2) and diagnostic/latency work (US3) can proceed independently, then meet at the release gate.

## Implementation strategy

MVP is T001–T009: model-free guard-only setup with real safe-pass/block checks. Keep it behind `--guard-only` until the measured gate passes. Add optional model compatibility and diagnostics next. Flip the default only after the final corpus, latency, ownership, and paired-task evidence is reviewable.
