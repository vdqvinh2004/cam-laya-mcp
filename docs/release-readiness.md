# v0.1.0 release readiness — 2026-09-25

**Status: experimental; not qualified for productivity or cost claims, and no live client rollout is verified on this Mac.** The package and local MLX runtime are present. Use `cam-laya-mcp doctor` as the host-specific integration check.

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
- 59 tests pass; Codex evaluation runner self-check passes.
- `uv build` produces the source distribution and wheel; `git diff --check` passes.
- `doctor` was read-only. Live Codex/OpenCode configuration was not changed during this check.

Raw paired data: [`codex-efficacy-results.json`](codex-efficacy-results.json). Evaluation details: [`codex-efficacy-baseline.md`](codex-efficacy-baseline.md).

## Release gates

1. Keep clear states on deterministic rules and MLX opt-in for unresolved choices. Keep post-test guidance and PostToolUse registration off by default; before enabling them by default, show that a controlled repeat catches and fixes known reviewable defects without a material response or token cost. Do not lower confidence thresholds to force uncertain model choices.
2. Verify Codex setup end to end in the user's active home, including hooks trust and one real task. Verify OpenCode without taking over its existing plugin, or document it as manual-only.
3. Require no coding-quality regression and at least 10% lower median time on the eligible paired cohort, with the paired interval excluding zero, before claiming a speed gain. Measure actual billing before claiming cost savings.
4. Build and inspect the package from the final tested commit. Test each client named as supported, then tag the release.

OpenCode has no documented user-prompt hook or nonblocking precommit hint channel. MCP registration alone never guarantees agent tool use. These limits remain in the release notes.
