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

## Phase 3: Milestone 4 — Codex efficacy and cost measurement

Baseline: `docs/codex-efficacy-baseline.md`. The initial matched-question smoke run showed no latency gain and did not exercise a Laya decision; it did not capture token usage or cost. Do not claim savings until a task-level comparison measures them.

- [x] T024 Define five repeatable Codex tasks covering routing, failed-test guidance, review guidance, repeated routing/cache behavior, and bypass.
- [x] T025 Add a runner for paired Codex sessions with matched model and prompts; only the Laya hooks/MCP integration differs.
- [x] T026 Record elapsed time, token counts, Laya stats, calls/errors, and task markers; label billed cost unavailable.
- [x] T027 Run one matched pair per task and document totals, medians, and measurement limits in `docs/codex-efficacy-baseline.md`.
- [x] T028 Optimize the largest measured regression or missed opportunity, then rerun the same evaluation and preserve the before/after report. Carried into Milestone 5; current data identifies duplicate routing and overall token/latency overhead.

## Phase 4: Milestone 5 — Measurable Codex efficiency

Evidence and design: `research.md`, `plan.md`, `data-model.md`, `contracts/milestone-5.md`, and `quickstart.md`. Milestone 4 used 25.2% more total tokens and took 33.3% longer by median with Laya enabled. Its five prompts measured tool availability more than coding value. T028 closes only after the Milestone 5 rerun and before/after report.

### Foundation: correct transport and observe cost

- [x] T029 Fix `src/laya_agent/daemon.py` so a connected request is never resent after a response timeout; retry only daemon connection/startup failures. Add timeout and mandatory-safety fallback checks in `tests/test_core.py`.
- [x] T030 Add bounded per-invocation outcome and stage timings in `src/laya_agent/runtime.py`, `src/laya_agent/daemon.py`, and `src/laya_agent/policy.py`; distinguish load, inference, queue, transport, cache, deterministic, defer, timeout, and failure without logging raw task text.
- [x] T031 Extend `benchmarks/evaluate_codex.py` and its self-check to correlate decision events to a trial, time the whole path including daemon startup and first useful response, and report run-specific latency rather than cumulative `average_latency_ms`.

### User story 1 (P1): trustworthy comparison

Goal: attribute overhead and judge real coding outcomes. Independent check: a repeated, counterbalanced trial has the same source snapshot, task, model, and verification on both sides; incomplete trials remain failures.

- [x] T032 [US1] Add no-Laya, hooks-only, MCP-only, and combined diagnostic profiles plus balanced run order and separate cold/warm cohorts to `benchmarks/evaluate_codex.py`; keep the five existing prompts as overhead probes.
- [x] T033 [P] [US1] Add at least six actual edit tasks, fresh disposable checkout creation, task-specific executable checks, and a fixed patch rubric in `benchmarks/codex_coding_tasks.json` and `benchmarks/evaluate_codex.py`; do not grade success by answer words or forced MCP calls.
- [x] T034 [US1] Run the four-profile diagnostic from `benchmarks/evaluate_codex.py`; record per-policy/tool overhead and select hook, MCP, or combined routing ownership with evidence in `docs/codex-efficacy-baseline.md`.

### User story 2 (P1): selective, safe invocation

Goal: an unchanged task gets no duplicate model inference or hint; a cold or trivial decision cannot block an ordinary task for longer than its value. Independent check: cache invalidation and hard/mandatory safety still pass through hook and MCP paths.

- [x] T035 [US2] Apply the selected route owner in `src/laya_agent/hooks.py` and `src/laya_agent/mcp_server.py`; remove redundant automatic route instructions/hints and keep explicit changed-state MCP access. Cover the lifecycle in `tests/test_integrations.py`.
- [x] T036 [US2] Define safe task identity and invalidation across hook/MCP state in `src/laya_agent/context.py`, `src/laya_agent/policy.py`, and `src/laya_agent/daemon.py`; remove unconditional cache clearing for an unchanged request. Cover changed task, repository, config, model, and relevant MCP context in `tests/test_core.py`.
- [x] T037 [US2] Gate cold and low-value model work before inference, and make the recent-latency gate recover after slow samples in `src/laya_agent/hooks.py` and `src/laya_agent/policy.py`; use measured stage budgets and cover bypass/recovery in `tests/test_core.py`.
- [x] T038 [P] [US2] If T034 attributes material cost to MCP registration, compare the current seven-tool surface with a compact variant in `src/laya_agent/mcp_server.py` using `benchmarks/evaluate_codex.py`; keep a product change only if tokens/turns fall without lower decision accuracy or breaking the read-only contract in `tests/test_mcp_roundtrip.py`. Condition not met: the bypass prompt differed by one token without a tool call, so the surface remains stable.
- [x] T039 [US2] Recheck hard-risk, mandatory-safety, timeout, cache, and client-config ownership behavior in `tests/test_core.py`, `tests/test_integrations.py`, and `tests/test_mcp_roundtrip.py` after invocation changes.

### User story 3 (P2): demonstrated net benefit

Goal: ship a typed policy only when it improves eligible coding tasks without lower quality or safety. Independent check: a repeated paired comparison reports eligible, all-task, bypass, cold, and warm results with token and time uncertainty.

- [x] T040 [P] [US3] Create labeled compact ambiguous test/review/action states in `benchmarks/decision_cases.json` and compare Laya-MLX against current rules and a simple deterministic baseline in `benchmarks/evaluate_decisions.py`; reject policies that add no actionable accuracy.
- [x] T041 [US3] Keep only policies that pass T040, and make their output change a measurable agent action in `src/laya_agent/policy.py`, `src/laya_agent/hooks.py`, or `src/laya_agent/mcp_server.py`; add one focused behavior check in `tests/test_core.py` or `tests/test_integrations.py` per selected policy.
- [x] T042 [US3] Run five counterbalanced baseline/selected pairs for each of at least six coding tasks with `benchmarks/evaluate_codex.py`; save a new aggregate artifact at `docs/codex-efficacy-milestone5.json` without overwriting the Milestone 4 result.
- [x] T043 [US3] Report per-task paired deltas, 95% paired bootstrap intervals, task-check/patch quality, first response, total and p95 time, cached/uncached/output tokens, tool turns, model stages, and billed-cost availability in `docs/codex-efficacy-baseline.md`; label any public-rate API-equivalent estimate separately.
- [x] T044 [US3] Apply the release gate in `specs/001-cam-laya-mcp/plan.md`: keep beneficial policies enabled in `src/laya_agent/policy.py`, disable ineffective policies there by default, record negative results in `docs/codex-efficacy-baseline.md`, and close T028 only after the before/after evaluation and `uv run pytest -q` plus `git diff --check` pass.

### Dependencies and delivery

T029 → T030 → T031 → T032 → T034. T033 can run alongside T032 after T031. T034 chooses the route design before T035–T038. T036 follows T035; T039 follows T035–T038. T040 can run alongside T035–T038; T041 needs T040 and the selected invocation path. T042 needs T033, T039, and T041; T043–T044 follow T042.

### User story 4 (P2): retrieve useful repository context

Goal: determine whether one bounded local search MCP call can replace agent search/read turns on repository-discovery tasks. Plan and contract: `specs/001-cam-laya-mcp/milestone-6-plan.md` and `specs/001-cam-laya-mcp/contracts/milestone-6.md`.

- [x] T045 [P] [US4] Investigate Milestone 5 usage, decision accuracy, existing context helpers, and retrieval alternatives; record evidence and stop conditions in `specs/001-cam-laya-mcp/milestone-6-research.md`.
- [x] T046 [US4] Specify the optional repository context retrieval story and its independent acceptance criteria in `specs/001-cam-laya-mcp/spec.md`.
- [x] T047 [US4] Define the bounded `laya_find_context` MCP request/response, repository boundary, privacy limits, and agent use guidance in `specs/001-cam-laya-mcp/contracts/milestone-6.md`; record architecture, evaluation, release gate, and delivery order in `specs/001-cam-laya-mcp/milestone-6-plan.md`.
- [x] T048 [US4] Prototype a deterministic local `laya_find_context` MCP tool and bound repository search; remove the prototype after Codex did not use it in the gated pilot.
- [x] T049 [US4] Expose the prototype only in the isolated experiment profile and try the one planned discovery guidance adjustment; leave the installed MCP surface unchanged after the adoption gate failed.
- [x] T050 [US4] Check repository confinement, query/result caps, ignored/generated/binary/secret/symlink exclusions, no-content logging, and empty results in focused unit and MCP roundtrip checks.
- [x] T051 [US4] Create six disposable coding tasks: four hidden-target discovery tasks with decoys and two named-target bypass tasks, each with an expected path, executable check, and patch rubric.
- [x] T052 [US4] Add isolated baseline, registered-but-unused, and context profiles with retrieval call, response-size, candidate, and handler-latency attribution; preserve both pilot artifacts without transcripts.
- [x] T053 [US4] Run the required discovery/bypass pilot and one guidance adjustment; adoption failed because Codex made zero retrieval calls on all four discovery trials.
- [x] T054 [US4] Stop before the full paired run because the explicit T053 adoption gate failed; retain `docs/codex-context-m6-pilot.json` and `docs/codex-context-m6-pilot-guidance.json`.
- [x] T055 [US4] Record the negative result and keep the experimental tool removed and disabled; do not claim token or response-time benefit from the pilot.

T045–T047 complete the research and planning before code changes. T048 precedes T049–T050; T051–T052 can proceed in parallel after the contract. T053 requires the tool and fixtures; T054 requires a successful pilot; T055 follows the full evaluation.
