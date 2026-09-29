# v0.1.0 release readiness — 2026-09-25; Milestone 7 refresh 2026-09-28; Milestone 9 closeout 2026-09-29

**Status: guard-only default passed local gates; model advice remains experimental and unqualified for productivity or cost claims.** An isolated live Codex hook trial passed; active-home trust and OpenCode/Claude live execution remain unverified. Use `cam-laya-mcp doctor` as the host-specific integration check.

## Milestone 9 measured context acceleration — negative result, candidate removed

G0 delivery passed (disposable `UserPromptSubmit` probe: hook fired, agent used the hinted path; `docs/context-hook-probe.json`). G2 passed (100-lookup p95 10.66 ms ≤ 250 ms; guard corpus 299/299; live Codex safe-pass/destructive-deny; `docs/context-pilot.json`). G1 pilot **failed**: live rerun hit 2/4 discovery targets in the top three (gate: 4/4), 0/2 bypass hints correct, quality 5/6 candidate vs 6/6 guard-only (one independent edge-check miss). Likely cause: live workdirs contain the whole repository tree, so generic prompt terms match many unrelated tracked files and crowd the target out. The single permitted pilot adjustment (test-file matches credited to their module) did not fix live ranking. Per the stop rule the 12-task main study (T018–T020) was skipped, the candidate and its prompt-hook registration were removed (T022), and guard-only behavior is unchanged. Evidence kept: `benchmarks/codex_context_tasks.json`, `docs/context-corpus-audit.json`, `docs/context-pilot.json`, `docs/context-pilot-runs.json`. No efficiency or billed-cost claim follows.

Closeout verification (T024, 2026-09-29): `pytest` 104 passed; evaluator and summarizer self-checks passed; guard corpus 299/299 with hook p95 40.19 ms; MCP stdio initialize roundtrip passed; `uv build` produced wheel+sdist; `git diff --check` clean; read-only `doctor` (codex configured_unverified, claude absent, opencode absent). Hosted CI still awaits a pushed commit.

| Requirement | Status | Evidence |
| --- | --- | --- |
| Local platform and runtime | Pass on this Mac | `doctor` reports Apple Silicon/macOS 27, isolated Python 3.12.14, Laya-MLX 0.2.0, MLX 0.32.2, and a downloaded model cache. |
| Codex installation | Temporary profile verified; live profile unverified | `CodexAdapter.validate()` passed in a temporary `CODEX_HOME`; a one-task Codex run invoked the post-test hook. The user's active Codex profile still has no project hooks/MCP, and trusted-hook review in a normal session remains unverified. |
| OpenCode installation | Unverified | `doctor` finds a plugin file but reports MCP absent and no client connection. The existing plugin is not owned by this installer, so setup must not overwrite it. |
| Claude Code | Not available here | Claude is not detected. A live Claude session remains necessary before claiming support was verified. |
| Coding productivity | **Fail** | The corrected isolated 27-run screen showed no reliable speed gain: paired median change +0.75 s with three Laya hooks (95% CI -5.45 to +7.14), and +2.93 s with PreToolUse+PostToolUse (-1.84 to +18.44). A six-pair PreToolUse-only screen was inconclusive (+1.14 s, 95% CI -9.12 to +8.255). A three-pair silent PostToolUse screen showed +10.48 s, but is exploratory. One full-hook run failed its patch/check quality gate. |
| Token/cost savings | **No saving demonstrated; billed cost unknown** | PreToolUse+PostToolUse increased paired median use by 17,469 tokens with the hint active (95% CI +16,476 to +33,651); an exploratory three-pair silent PostToolUse screen also increased tokens by 16,491. Three-hook and PreToolUse-only estimates crossed zero. API-equivalent estimates are not Codex bills; actual spend was not measured. |
| Model usefulness | Hint adoption observed; post-test benefit not demonstrated | In the corrected tracked-fixture screen, post-test `git diff` appeared in 7/9 full-hook and 9/9 PreToolUse+PostToolUse runs vs. 0/9 baseline, with no post-test edits. A controlled injected Unicode-digit defect remained unfixed in all 5 hook trials despite 4/5 running `git diff`. Post-test guidance and its PostToolUse registration are now off by default; set `post_test_guidance = true` and rerun setup to opt in. See [adoption data](codex-hook-event-followup.json), [defect screen](codex-review-defect-followup.json), and earlier [quality data](codex-review-quality-pilot.json). |
| Safety and privacy | Pass by design; keep verifying | Deterministic hard-risk rules stay active with model decisions disabled. Prompts/commands are not written to event logs. Existing automated coverage includes fallback and integration ownership paths. |

## Current verification

- Latest default-profile screen: 6 paired runs; baseline passed 5/6 and current SessionStart + PreToolUse profile passed 6/6. Time and token confidence intervals cross zero, and the one baseline `retry_review` miss was unrelated to a Laya decision. Treat as exploratory; no performance, cost, or review benefit is established.
- Disposable Codex adapter smoke: registered only `cam-laya-mcp` with `SessionStart` and `PreToolUse`; both hook commands exited 0, and uninstall completed. A real `codex exec` task could not run because the isolated profile had no authentication; Codex hook trust and a real task remain unverified. Scratch profile was removed; live settings were untouched.
- 85 tests pass (includes Milestone 2 shell-scan regressions through `hard_risk`, `DecisionEngine`, and the Codex hook); Codex evaluation runner self-check passes.
- `uv build` produces the source distribution and wheel; `git diff --check` passes. Wheel payload inspected in Milestone 7: `laya_agent` package modules plus metadata (sdist is the full source tree).
- `doctor` was read-only. Live Codex/OpenCode configuration was not changed during this check. Fresh 2026-09-28 snapshot: darwin-arm64, macOS 27.0, isolated Python 3.12.14, Laya-MLX 0.2.0, MLX 0.32.2, model cache present; live Codex hooks/MCP absent, OpenCode MCP disconnected with an unowned plugin file present, Claude Code absent.

Raw paired data: [`codex-efficacy-results.json`](codex-efficacy-results.json). Evaluation details: [`codex-efficacy-baseline.md`](codex-efficacy-baseline.md).

## Release gates

1. Keep clear states on deterministic rules and MLX opt-in for unresolved choices. Keep post-test guidance and PostToolUse registration off by default; before enabling them by default, show that a controlled repeat catches and fixes known reviewable defects without a material response or token cost. Do not lower confidence thresholds to force uncertain model choices.
2. Verify Codex setup end to end in the user's active home, including hooks trust and one real task. Verify OpenCode without taking over its existing plugin, or document it as manual-only.
3. Require no coding-quality regression and at least 10% lower median time on the eligible paired cohort, with the paired interval excluding zero, before claiming a speed gain. Measure actual billing before claiming cost savings.
4. Build and inspect the package from the final tested commit. Test each client named as supported, then tag the release.

OpenCode has no documented user-prompt hook or nonblocking precommit hint channel. MCP registration alone never guarantees agent tool use. These limits remain in the release notes.

## Milestone 8 offline safety default — 2026-09-28

Plain `setup` now installs owned PreToolUse checks without MLX, `uv`, daemon startup, or MCP registration for new users. `setup --with-model` and legacy `setup --yes` remain explicit model paths. Existing model-enabled preferences and healthy owned access survive setup. The local Milestone 8 gates passed; no productivity, token-savings, or billed-cost claim follows.

| Gate | Result | Evidence |
| --- | --- | --- |
| SC-001 platform setup | Pass on Mac and local Ubuntu container | Plain `setup` passed disposable Mac and Ubuntu 24.04 profiles with fake client binaries, no `uv`, model files, or MCP entry; repeat setup and uninstall passed. The hosted GitHub Actions job is configured but has not run on a pushed commit. |
| SC-002 covered corpus | Pass for frozen cases | `benchmarks/evaluate_guard.py`: locked destructive 112/112, locked benign 113/113, holdout destructive 35/35, holdout benign 39/39. This checks the documented static risk families, not arbitrary scripts. |
| SC-003 hook latency | Pass on reference Mac | 100 whole-process `git status` hooks: median 37.44 ms, p95 41.09 ms, maximum 43.11 ms; no denial or daemon start. Earlier baseline p95 was 104.9 ms. Ubuntu container: 20 samples, p95 46.08 ms. |
| SC-004 ownership and live client | Codex pass; other live clients unverified | Disposable Codex, Claude, and OpenCode config tests preserve unowned entries. [Live Codex trial](guard-live-trial.json): one safe hook pass and one destructive hook denial; target remained. Trial used isolated credentials/config and explicit trust bypass. Claude is absent; OpenCode is installed, but isolated authentication timed out before a live trial. |
| SC-005 paired coding | Pass for nonregression | [Coding screen](guard-coding-screen.json): six tasks, 18 matched pairs, 18/18 checks in each profile, 75 observed guard hook calls, zero MCP calls. Median paired changes: time −3.88%, tokens −1.07%. An earlier network-disrupted attempt was discarded and rerun. These results do not meet the separate productivity-claim gate. |
| SC-006 diagnostics | Pass | `doctor` separates owned guard configuration, unverified live execution/trust, model preference, runtime availability, cache, and MCP presence. Configured hooks are not labeled as live verified; its inspected live config files were byte-for-byte unchanged. |

The final local suite passed 104 tests on Mac and 104 tests in the Ubuntu container. MCP stdio roundtrip passed, the local MLX smoke returned `inspect`, the evaluator self-check passed, and the wheel plus source distribution built. The hosted GitHub Actions run remains pending a push. OpenCode and Claude live execution remain unverified, so only Codex is named as live verified.
