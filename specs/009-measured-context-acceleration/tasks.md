# Tasks: Measured Context Acceleration

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [context-hook contract](contracts/context-hook.md), [validation guide](quickstart.md)

**Status**: Closed 2026-09-29 with a negative result. All 24 tasks resolved (19 executed, T018–T020 skipped per stop rule after G1 failed). Candidate removed; guard-only unchanged.

**Stop rule**: G0, G1, G2, G3, or G4 failure ends rollout work. Remove any context candidate, record the failed gate, and preserve Milestone 8 guard-only behavior.

## Phase 1: Setup and frozen evidence

**Purpose**: Establish the baseline and prove the client event exists before building lookup code.

- [x] T001 Record the Milestone 8 source revision, local evidence, and hosted CI status in `specs/009-measured-context-acceleration/research.md`; identify any release failure that must be fixed before Milestone 9 rollout.
- [x] T002 Run one disposable, trusted Codex `UserPromptSubmit` probe using the documented `prompt` input and JSON `additionalContext` output; record Codex version, trust mode, delivery result, and no raw prompt in `docs/context-hook-probe.json`. If G0 fails, skip candidate work and proceed to the closeout tasks.
- [x] T003 Freeze `benchmarks/codex_context_tasks.json` with two pinned repository revisions, six separate pilot tasks (four discovery, two bypass), and 12 untouched main tasks (eight discovery, four bypass); each task must include an independent check, allowed changes, and its cohort.
- [x] T004 Validate all 18 fixtures in `benchmarks/codex_context_tasks.json`: starting revision reproduces the defect or requested change, the independent check distinguishes a correct patch, prompts hide paths in discovery tasks, and no main task is used for lookup tuning; record the audit in `docs/context-corpus-audit.json`.

## Phase 2: Foundational benchmark work

**Purpose**: Reuse the existing paired runner and freeze analysis before measuring the candidate.

- [x] T005 Add an isolated `context` profile alongside existing `hooks_pre` in `benchmarks/evaluate_codex.py`; both profiles must have identical model settings, model advice off, guard PreToolUse on, no MCP server, and disposable config/workspaces.
- [x] T006 Extend `benchmarks/evaluate_codex.py` to record context-hook receipt, hint bytes/lookup time, first hinted-path use, discovery-action counts, quality checks, and prespecified infrastructure failure categories without retaining raw prompts, transcripts, source, or commands.
- [x] T007 [P] Extend `benchmarks/summarize_codex.py` with paired percentage changes and task-cluster 95% bootstrap intervals for the frozen discovery cohort; keep bypass separate and label `api_equivalent_usd` as a published-price estimate, never billed cost.
- [x] T008 Add one runnable self-check for context-profile isolation and event/statistics parsing in `benchmarks/evaluate_codex.py`, and one for clustered paired reporting in `benchmarks/summarize_codex.py`.

**Checkpoint**: The untouched main corpus and analysis method are frozen. Only the six pilot tasks may guide a candidate adjustment.

## Phase 3: User Story 1 - Automatic relevant context (Priority: P1) 🎯 MVP

**Goal**: Deliver a safe, bounded local path hint through Codex's native prompt event.

**Independent Test**: A disposable Codex task without a named file receives at most three safe paths; an explicit-target task receives no hint; existing destructive-action denial still works.

- [x] T009 [P] [US1] Add `context_hint = false` as the new-install default and preserve an existing explicit value in `src/laya_agent/config.py`.
- [x] T010 [P] [US1] Implement a bounded tracked-path lookup in `src/laya_agent/context.py`: at most three distinct repository-local paths, 800 output characters, no symlink escape or secret/generated/vendor path, no model/index/cloud call, and no raw prompt log.
- [x] T011 [US1] Return neutral `UserPromptSubmit` `additionalContext` only for a qualifying prompt in `src/laya_agent/hooks.py`; return no context for explicit targets, low confidence, timeout, or lookup error, without changing `PreToolUse` safety behavior.
- [x] T012 [US1] Register or remove only the owned Codex prompt hook when the context preference changes in `src/laya_agent/integrations.py`; preserve unrelated hooks and existing guard matcher/event ownership.
- [x] T013 [US1] Surface opt-in setup and separate installed-versus-live context status in `src/laya_agent/cli.py`; leave the default guard-only, model preference, and MCP state intact.
- [x] T014 [US1] Add focused lookup, bypass, timeout, secret-path, and hook-output checks in `tests/test_core.py`; verify one path hint cannot bypass a covered destructive denial.
- [x] T015 [US1] Add owned install/repeat/disable/uninstall and unowned-entry preservation checks in `tests/test_integrations.py`; test `UserPromptSubmit` is absent from a new guard-only profile.
- [x] T016 [US1] Measure 100 qualifying prompt lookups, run the locked guard corpus and an isolated Codex safe-pass/destructive-deny trial, and record G2 latency/safety results in `docs/context-pilot.json`; stop if existing guard gates regress.

**Checkpoint**: Context delivery is opt-in and live verified on Codex; routine guard behavior still passes.

## Phase 4: User Story 2 - Measured task gain (Priority: P1)

**Goal**: Make a reproducible quality, speed, token, and cost decision using untouched coding tasks.

**Independent Test**: The main report contains 48 matched pairs from 12 untouched tasks, both profiles pass at least 95% of checks, and a prespecified gate decision follows the paired intervals.

- [x] T017 [US2] Run the six pilot tasks once per `hooks_pre` and `context` profile with counterbalanced order; require 4/4 discovery targets in top three, 0/2 bypass hints, live hook receipt, and no quality regression in `docs/context-pilot.json`. Permit at most one recorded pilot-only adjustment in `src/laya_agent/context.py` and rerun the pilot after it, then freeze code. **Gate FAILED**: live rerun 2/4 discovery hits, 0/2 bypass correct, quality 5/6 vs 6/6; adjustment spent; code frozen without opening the main set.
- [x] T018 [US2] Record candidate and corpus hashes plus projected 96-run time, tokens, and attributable spend in `docs/context-pilot.json`; open the untouched 12-task main set and evaluate G1 relevance (at least 7/8 top-three discovery targets, 0/4 bypass hints, zero unsafe paths) without any further tuning. **Skipped: G1 pilot failed; main set never opened.**
- [x] T019 [US2] Run four counterbalanced matched pairs per main task (48 pairs, 96 runs) with `benchmarks/evaluate_codex.py`; save bounded observations, check results, exclusions, and run settings to `docs/context-study.json`. **Skipped: G1 pilot failed.**
- [x] T020 [US2] Produce `docs/context-study-summary.json` with task-cluster intervals, quality floor, bypass overhead, delivered-hint counts, and G3/G4 decisions; add actual provider charges only if attributable per-run billing exists, otherwise mark G5 unverified. **Skipped: G1 pilot failed; G3/G4/G5 unverified by stop rule.**
- [x] T021 [US2] Record the full pass/fail/skip decision, negative results, infrastructure exclusions, and any supported time/token/cost claim in `docs/release-readiness.md`; do this even if an early gate skipped the main study, and do not promote context after a failed or unverified G0–G4 gate.

**Checkpoint**: A reviewer can reproduce the claimed result or see exactly why rollout stopped.

## Phase 5: User Story 3 - Safe rollout and clear status (Priority: P2)

**Goal**: Keep guard-only predictable and describe the actual supported context mode.

**Independent Test**: Repeat setup and uninstall in disposable profiles; unrelated entries and guard denial survive, and doctor does not call an untrusted hook live verified.

- [x] T022 [US3] If G0–G4 pass, keep Codex context behind the explicit preference and run a normal trusted-profile trial; if a gate fails, remove the candidate and prompt-hook registration from `src/laya_agent/context.py`, `src/laya_agent/hooks.py`, `src/laya_agent/integrations.py`, `src/laya_agent/config.py`, and `src/laya_agent/cli.py`. **Gate failed: candidate removed; guard-only intact; benchmark evidence and plumbing retained.**
- [x] T023 [US3] Update `README.md` and `specs/README.md` with the actual Milestone 9 result, opt-in command/configuration if supported, the measured cohort, and explicit Claude Code/OpenCode limits; do not state a default or billed-cost gain without its gate. **Recorded negative result; no opt-in ships; no gain claimed.**

## Phase 6: Final verification

- [x] T024 Run full `uv run pytest -q`, guard corpus, MCP stdio roundtrip, `uv build`, `git diff --check`, and read-only `cam-laya-mcp doctor`; record exact results and any hosted CI limit in `docs/release-readiness.md` and close `specs/009-measured-context-acceleration/plan.md` with the observed gate outcome. **All green locally; hosted CI still pending a push; milestone closed negative.**

## Dependencies & execution order

T001–T002 precede candidate work; G0 failure skips T003–T020 but still requires T021–T024 closeout. T003–T004 freeze the pilot and untouched main fixtures before T009–T016 candidate work. T005–T008 make the paired measurement reproducible. T009–T015 build the opt-in slice; T016 proves safety and latency. T017 alone may drive one adjustment; T018 freezes and opens the main set. Any later gate failure skips dependent study work but still requires T021–T024. T019–T021 decide efficacy, then T022–T024 close rollout and documentation. Milestone 8 hosted CI must pass before any default change, not before a disposable experiment.

## Parallel opportunities

T007 can run alongside T005–T006 after the corpus is frozen. T009 and T010 touch separate files after G0. The separate core and integration tests in T014–T015 can be prepared alongside the corresponding code once the contract is fixed. No parallel work may expose or tune against the untouched main set before T018.

## Implementation strategy

MVP is T001–T016: a live verified, opt-in, safe path hint with no performance claim. T017 is a cheap stop gate. Only after it passes do T018–T020 spend the full 96 runs. A failed efficacy gate still produces a useful result: guard-only remains the product and the experiment is removed.
