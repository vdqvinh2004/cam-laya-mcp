# Tasks

## Research and design

- [x] T001 Research current Laya-MLX, MCP, Codex, Claude Code, and OpenCode APIs.
- [x] T002 Record client capability matrix and ADR.

## Core

- [x] T003 Implement Laya-MLX wrapper, compact state, deterministic policy, and cache.
- [x] T004 Implement shared local process and seven MCP tools.

## Installation and clients

- [x] T005 Implement CLI, setup approval flow, doctor, benchmark, stats, and uninstall.
- [x] T006 Implement Codex and Claude native hooks, OpenCode plugin, and MCP config ownership.

## Verification and documentation

- [x] T007 Add unit tests, client adapter tests, and actual MCP stdio roundtrip test.
- [x] T008 Write README, license, and Spec Kit records.
- [x] T009 Run real Laya-MLX checkpoint smoke inference after explicit installation approval.
- [x] T010 Run detected client end-to-end smoke tests after setup (Codex and OpenCode available; Claude Code boundary tested with fixtures).

## Phase 1: Convergence — Milestone 2 production hardening

- [x] T011 Fail closed for risk checks when `mandatory_safety` is enabled and the daemon/MCP fails; add hook and MCP regression tests (request §§49–50; partial).
- [x] T012 Cache repeated task classifications and ambiguous risk decisions using safe hashed inputs; invalidate on task, repository, action, config, and model changes without retaining raw secrets (request §§31–32; contradicts current spec scenario 5).
- [x] T013 Make automatic lifecycle decisions cover meaningful code/test transitions, and make `should_call_laya` consider event, prior state, cache, and latency without calling on every tool result (request §§5–7, 35, 56–57; partial).
- [x] T014 Report decisions by policy and escalations, retain honest source and estimated-savings attribution, and bound local event logging (request §§46, 51–53; partial).
- [x] T015 Recheck current Laya-MLX Router, `choice`, `score`, `noul`, and presets; use any that improve a concrete policy and document deliberate exclusions (request §§1, 3, 33, 62; partial).
- [x] T016 Exercise setup, doctor, uninstall, unsupported/missing model, config corruption, and stale-daemon recovery; fix reproducible failures while preserving unrelated client config (request §§8–9, 42–45, 64, 67–68; partial).
- [x] T017 Verify real Codex and OpenCode integration after refresh, test Claude Code adapter at the client boundary when its binary is absent, and document each client's automatic-invocation limit (request §§35–39, 59, 67; partial).
- [x] T018 Add focused failure and concurrency checks for invalid state/policy, timeout, inference crash, cache corruption, socket limits, and mandatory safety (request §§48, 66–68; partial).
- [x] T019 Update spec, plan, ADR, README, example workflow, and milestone acceptance to match implemented behavior; run full tests, lint, build, smoke, benchmark, and doctor (request §§69–75; partial).

## Phase 2: Convergence — Milestone 3 upgrade and configuration safety

- [x] T020 Reuse a healthy owned isolated runtime on repeat setup, and ensure setup chooses an executable that can actually import Laya-MLX when it is installed outside the CLI environment, per scenario 1 and T005 (partial).
- [x] T021 Validate installed Codex and Claude hooks by their owned command entries, and replace stale owned paths without creating duplicate hooks when the executable moves, per acceptance 20–21 and T006 (partial).
- [x] T022 Upgrade owned OpenCode MCP entries and plugin executables when the command path changes, while refusing to overwrite unowned entries, per acceptance 20–21 and T006 (partial).
- [x] T023 Preserve comments in active OpenCode JSONC configuration through setup and uninstall, per acceptance 21 and T006 (partial).
