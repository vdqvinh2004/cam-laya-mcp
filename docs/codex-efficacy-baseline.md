# Codex efficacy evaluation

Date: 2026-09-24. Host: Apple Silicon, macOS 27.0, Python 3.14.6. Codex model: `gpt-6-luna`.

## Method

- Five matched tasks, one paired run each: task routing, failed-test guidance, review guidance, repeated routing/cache, and bypass.
- Same Codex model and prompts. Baseline disabled Laya hooks and MCP; enabled used installed Codex hooks plus this checkout's MCP source in the isolated Python 3.12 MLX runtime.
- Captured Codex token counts, elapsed time, Laya stats, MCP calls/errors, and a task marker check. Raw aggregate run records: `docs/codex-efficacy-results.json`; runner and task definitions: `benchmarks/evaluate_codex.py` and `benchmarks/codex_tasks.json`.

## Results

| Measure | Baseline | With Laya |
|---|---:|---:|
| Input tokens | 146,425 | 183,656 |
| Output tokens | 717 | 613 |
| Total tokens | 147,142 | 184,269 |
| Median elapsed time | 17.91 s | 23.87 s |
| Task marker checks | 5/5 | 5/5 |

The enabled condition used 25.2% more total tokens and was 33.3% slower by median. It made four MCP calls with zero errors and recorded one cache hit. The repeated-task record shows three `route_task` requests for one task (one hook and two MCP calls). All five marker checks passed, but this is only a completion proxy; no human quality review was performed. Billed USD cost was unavailable. Using the [published `gpt-6-luna` Standard short-context API rates](https://developers.openai.com/api/docs/pricing) on uncached input, cached input, and output gives an illustrative $0.00461 baseline versus $0.00510 with Laya (+10.7%); this is not the Codex bill. This single run per task has no variance estimate.

## Conclusion

This integration did not improve measured performance or token efficiency in this evaluation. The current tasks explicitly ask for MCP calls and do not assess coding quality, so Milestone 5 adds actual coding tasks and isolates hook, MCP, and model overhead. The runner stores aggregate metrics and deliberately omits session transcripts.

## Milestone 5 diagnostic (before routing change)

Five diagnostic prompts ran once in each profile with `gpt-6-luna`, low reasoning effort, cold local state, and matched prompts. These runs use shorter instructions than the Milestone 4 prompts, so compare profiles within this table only. Raw metrics: `docs/codex-diagnostic-m5.json`.

| Profile | Median wall time | Total Codex tokens | MCP calls | Marker checks |
|---|---:|---:|---:|---:|
| No Laya | 17.34 s | 129,158 | 0 | 4/5 |
| Hooks only | 16.80 s | 129,015 | 0 | 5/5 |
| MCP only | 21.36 s | 212,369 | 4 | 5/5 |
| Hooks and MCP | 24.76 s | 214,881 | 4 | 5/5 |

On the routing prompt, the hook profile took 24.33 s versus 19.56 s baseline; MCP registration without a call took 19.38 s. On the review and repeated-route prompts, forced MCP calls took about 56–59 s and roughly doubled token use. The baseline failed-test marker miss shows why these checks cannot judge task quality. Trial IDs did not reach the installed hook/MCP subprocesses in this diagnostic, so per-call daemon timings are unavailable here; the runner now injects IDs explicitly for subsequent runs. The selected design removes automatic prompt routing and keeps MCP for explicit, potentially useful decisions. A smaller MCP tool surface is not warranted by the bypass prompt (one token difference and no call).

## Milestone 5 decision policy screen

The 12 labeled compact states in `benchmarks/decision_cases.json` tested test-scope, review, and next-action choices. The simple deterministic baseline matched 12/12 labels; Laya-MLX matched 4/12 (`docs/codex-decision-m5.json`). These labels are a small screening set, not a general accuracy claim. No MLX policy beat simple rules or produced enough actionable accuracy to enable automatically, so T041 selected none. Existing explicit MCP access remains available for evaluation.

A new-source, tagged review trial confirmed attribution: one cold `laya_review_decision` call returned `defer_to_agent` after 36.88 s model load and 0.38 s inference; the MCP client spent 37.74 s total (`docs/codex-diagnostic-m5-tagcheck-review.json`). A warm trial of the same prompt returned the same defer result with 0.20 s inference and 0.21 s client time (`docs/codex-diagnostic-m5-warm.json`); its 14.71 s Codex elapsed time excludes the separate preload step. The revised prompt route did not call the model (`docs/codex-diagnostic-m5-tagcheck.json`).

## Milestone 5 paired coding evaluation

Six disposable Python edit tasks ran five counterbalanced baseline/combined pairs each with `gpt-6-luna` and low reasoning effort. Each run received an independent executable check and a patch rubric. Positive deltas below mean the combined profile used more tokens or took longer. Raw aggregate artifact: `docs/codex-efficacy-milestone5.json`; computed summary: `docs/codex-efficacy-milestone5-summary.json`. The only measured coding cohort was mixed local state; separate cold/warm coding estimates are unavailable because no coding run called the local model.

| Task | Check + patch pass, baseline → combined | Paired token delta median [95% CI] | Paired time delta median [95% CI], s |
| --- | ---: | ---: | ---: |
| clamp_fix | 5/5 → 5/5 | -198 [-16,784, 33,522] | +3.80 [-2.35, 12.29] |
| port_failure | 5/5 → 5/5 | +4,169 [-35,418, 35,657] | +3.35 [-295.67, 17.70] |
| stable_paths | 4/5 → 5/5 | +16,430 [-35,589, 33,995] | +9.17 [2.05, 12.67] |
| retry_review | 5/5 → 5/5 | -264 [-18,311, 17,287] | +4.10 [-2.48, 9.24] |
| config_merge | 4/5 → 4/5 | -1,091 [-20,066, 51,886] | +4.83 [3.50, 16.34] |
| test_scope | 5/5 → 5/5 | -9,481 [-52,859, 32,807] | +2.16 [-0.98, 18.26] |

| Aggregate | Baseline | Combined |
| --- | ---: | ---: |
| Check + patch pass | 28/30 | 29/30 |
| Total tokens | 2,543,136 | 2,536,378 |
| Uncached input / cached input / output | 284,045 / 2,245,120 / 13,971 | 282,014 / 2,240,000 / 14,364 |
| Median / p95 wall time | 29.63 / 41.32 s | 36.33 / 47.18 s |
| Median first useful response | 8.36 s | 8.45 s |
| Agent tool turns / test commands | 104 / 3 | 108 / 2 |
| MCP calls / hook decisions | 0 / 0 | 0 / 0 |
| API-equivalent cost | $0.05784 | $0.05778 |

The paired overall token delta was -138.5 [95% bootstrap CI -12,433.5, +2,647] tokens; the paired time delta was +4.515 [3.425, 7.805] seconds. Cached input was about 88.8% of input in both profiles. The eligible cohort had 15 runs per profile and 15/15 quality passes each; its median was 33.06 → 38.79 seconds, with paired time delta +3.76 [-0.82, 9.06] seconds and paired token delta +70 [-15,386, 4,874]. Bypass tasks had 13/15 → 14/15 quality passes and median 25.71 → 34.34 seconds, with paired time delta +4.87 [3.50, 11.38]. A baseline `port_failure` run took 333.02 seconds and passed; it is included in the data. The p95 over 30 runs does not include this single maximum, while the eligible five-run task p95 does.

No coding run used MCP or produced a hook decision. Local model load, inference, queue, and transport times for coding therefore have no observations; the cold tagged diagnostic above gives one direct local measurement. Codex billed cost was unavailable. The dollar row is a separate API-equivalent estimate using published `gpt-6-luna` Standard short-context rates accessed 2026-09-24, not a Codex bill.

The release gate fails: eligible tasks did not reduce median time, paired intervals do not show a token saving, and no model action caused the observed quality difference. New configurations now start with model decisions disabled; deterministic risk rules still apply, and users can opt in with `cam-laya-mcp enable`. Existing user config is preserved. This is a negative efficacy result, not a claim that Laya improved the coding agent.

## Milestone 6 retrieval pilot: stopped

The local search helper found an expected path in the top three results for all four hidden-target fixtures, and all six initial fixture checks failed. Codex did not call the tool on any of the four discovery trials in two three-task pilots: zero calls with the initial description and zero after one stronger instruction to search with MCP before shell commands. It also skipped the tool on the named-target bypass trials. The first pilot had one candidate quality failure; the adjusted-guidance pilot passed all checks. Artifacts: `docs/codex-context-m6-pilot.json` and `docs/codex-context-m6-pilot-guidance.json`.

The full paired evaluation was stopped at the planned adoption gate. These pilot samples do not establish a token or time effect. They do show that MCP registration and server guidance alone did not make the agent use the proposed action. The prototype was removed; no retrieval efficiency claim or default tool enablement follows from this experiment.

## Previous project decision (before the deterministic fallback)

The latest 36-run warm paired pilot does not meet the release gate for productivity or cost claims. Keep model inference opt-in, retain deterministic risk checks, improve model decision usefulness and client adoption, then repeat the paired evaluation. This result supersedes the earlier stop decision above; it does not establish a speed or token benefit.

## Pre-fallback warm paired pilot (superseded)

Six coding tasks ran three paired repetitions each with `gpt-6-luna`, low reasoning effort, and a warm MLX runtime (36 runs total). The combined profile passed 17/18 checks vs. 16/18 baseline; the eligible subset passed 8/9 in each profile. Both profiles had a 20.05 s median elapsed time. Paired time change was −1.04 s (95% CI −2.54 to +2.15 s); paired token change was −1,308 (95% CI −16,620 to +8,808). The time interval crosses zero and the observed median does not meet the 10% target. Codex API spend was not measured. Raw run data: [`codex-efficacy-results.json`](codex-efficacy-results.json).

Across the combined runs, Laya recorded 36 hook decisions: 3 `review_decision` model calls and 33 cache hits. All 3 model calls returned `defer_to_agent` with 0.083 confidence; warm inference took 123–230 ms. This pilot still fails the release gate for productivity or cost claims.

## Deterministic fallback update

After the pre-fallback pilot, the 12-state screen's deterministic rules were moved into shared policy and made the fast path for clear test/review transitions. Those rules matched all 12 expected labels; raw Laya choices matched 4/12. The screen is small and hand-labeled, so it supports a controlled hybrid experiment, not a general accuracy claim.

## Latest paired pilot: deterministic fallback

Six coding tasks ran three paired repetitions each with `gpt-6-luna`, low reasoning effort, and a warm local runtime (36 runs). Model decisions were enabled only in the temporary pilot config. Codex hooks and MCP were installed under a temporary `CODEX_HOME`; no live client config was changed. Each disposable coding snapshot now gets a clean local Git baseline before task files are overlaid, so hooks can observe task-level changed-file counts.

| Measure | Baseline | Combined |
| --- | ---: | ---: |
| Check and patch passes | 18/18 | 18/18 |
| Total tokens | 1,443,460 | 1,364,857 |
| Median elapsed time | 17.66 s | 17.36 s |
| Illustrative API-equivalent cost | $0.03206 | $0.03160 |

The paired median time change was +0.035 s (95% bootstrap CI -2.680 to +2.825 s). The paired token change was -2,129.5 (95% CI -17,336 to +2,270.5). Both intervals include zero. The eligible nine pairs all passed; their median time was 19.27 s baseline and 19.66 s combined, with paired time change +0.98 s (95% CI -5.4 to +4.6 s). The 10% time target and token-savings gate remain unmet. The dollar figures use published short-context API rates and are not Codex billing data.

The combined profile made 27 test-command calls and zero MCP calls. The artifact recorded zero daemon-backed hook decisions. At pilot time, deterministic hook returns bypassed the event logger, so these records cannot tell how many rule hints Codex received. A privacy-safe rule event is now logged for future evaluations; the pilot result remains a profile-level comparison without reliable rule-level attribution. Raw records: [`codex-efficacy-deterministic-pilot.json`](codex-efficacy-deterministic-pilot.json). Summary: [`codex-efficacy-deterministic-pilot-summary.json`](codex-efficacy-deterministic-pilot-summary.json).

A one-task `retry_review` smoke then ran through the temporary Codex profile. Codex executed one test command; the passing post-test hook logged `review_decision=self_review` with `source=hook` and `outcome=rule`, and the independent task check passed. This verified hook execution; it did not measure whether the agent acted on the hint. The temporary trace and auth copy were removed.

## Post-test hint adoption screen

The first three-pair screen used the abstract `Local post-test decision: self_review.` message. Codex ran an explicit `git diff` after a successful test in 0/3 baseline and 0/3 hook trials. Hook logs showed 2–3 review hints per run. Raw data: [`codex-review-adoption-pilot.json`](codex-review-adoption-pilot.json).

The follow-up changed the hint to a direct instruction: “Tests passed. Review `git diff` for unintended changes before finishing.” Across three paired `retry_review` runs, all six independent patch checks passed. Codex ran `git diff` after a successful test in 3/3 hook trials and 0/3 baseline trials; each hook trial logged two `self_review` hints. A neutral `stable_paths` task whose prompt did not mention review produced a post-test `git diff` in 2/3 hook trials and 0/3 baseline trials; all six checks passed. A further two-task screen (`strict_port`, `finite_percent`) yielded a `git diff` in 5/6 hook trials vs. 0/6 baseline. Across all four tasks, the action signal is 10/12 vs. 0/12. Raw data: [`codex-review-adoption-followup.json`](codex-review-adoption-followup.json), [`codex-review-adoption-heldout.json`](codex-review-adoption-heldout.json), and [`codex-review-quality-pilot.json`](codex-review-quality-pilot.json).

## Independent review-quality screen

The `strict_port` and `finite_percent` tasks ran independent edge checks after Codex finished: reject signed or non-ASCII port digits, and reject NaN/infinite percentages. Those checks passed in 12/12 runs across the earlier screen, with no post-test edits. A later controlled screen injected a Unicode-digit defect after visible tests passed. The visible check passed in 10/10 runs, but the independent check failed in 10/10; the Laya review hint prompted `git diff` in 4/5 hook runs and no run corrected the defect. Baseline prompted no `git diff` and also corrected none. This is evidence of hint adoption, not review quality. Raw data: [`codex-review-quality-pilot.json`](codex-review-quality-pilot.json) and [`codex-review-defect-followup.json`](codex-review-defect-followup.json).

## Current project decision

The project is not ready to claim faster coding or lower cost. The corrected screen found no reliable speed gain, one full-hook quality miss, and a significant token increase for PreToolUse+PostToolUse; the smaller PreToolUse-only screen was inconclusive. The injected Unicode-digit defect remained unfixed in all five review-hook trials. Post-test guidance and PostToolUse registration are now disabled by default; set `post_test_guidance = true` and rerun setup to opt in. Model decisions remain opt-in. Re-enable post-test guidance by default only after a controlled repeat shows it catches and fixes reviewable defects without a material cost penalty.

## Strict hook-isolation follow-up

The evaluator now builds each profile under a temporary `CODEX_HOME`, uses an empty scratch workspace, excludes `.codex` from coding snapshots, disables Codex plugins and the remote plugin catalog in both config and CLI flags, and audits the profile before and after each run. The [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference) says the remote plugin catalog is enabled by default. An earlier attempt that disabled only that catalog still populated plugin cache files; those runs were discarded. No live Codex config was changed.

Three eligible coding tasks (`retry_review`, `strict_port`, `finite_percent`) ran once per profile. All six pre-run and post-run audits passed. Baseline had zero hooks and zero MCP servers. The hook-only profile had three commands, each validated as `cam-laya-mcp hook codex <event>`, zero MCP servers, disabled plugins, and zero observed MCP calls. A self-check injects a fake third-party hook and confirms the profile builder removes it. Raw data: [`codex-isolation-pilot.json`](codex-isolation-pilot.json).

All six patch and independent checks passed; neither profile recorded a post-test edit. Codex ran `git diff` after a passing test in 3/3 hook trials and 1/3 baseline trials, with no defect caught. Median elapsed time was 24.18 s with hooks versus 20.32 s baseline (+19%); total input tokens were 260,914 versus 226,669 (+15%). This small rule-only screen shows no speed or token benefit and does not measure MLX inference or Codex billed cost.

## Corrected isolated hook screen

The evaluator accepts `--laya-executable` and builds a disposable manifest containing only Laya hooks. It leaves the live profile untouched and audits hook events, MCP servers, and plugin settings before and after every trial. The corrected 27-run screen committed each task fixture into its Git baseline; this supersedes the earlier screen, whose untracked fixtures made `git diff` counts unreliable. Three eligible coding tasks ran three repetitions in baseline, full-hook, and PreToolUse+PostToolUse profiles. All 27 isolation audits passed. Baseline had zero hooks and MCP servers. Hook profiles used only cam-laya-mcp commands, with zero MCP servers and zero MCP calls. All 18 applicable independent edge checks passed; the `retry_review` task has no independent edge check.

| Profile | Hook events | Patch/check quality | Edge checks | Median elapsed | Total tokens | `git diff` after test |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | none | 9/9 | 6/6 | 28.12 s | 649,630 | 0/9 |
| Three Laya hooks | SessionStart, PreToolUse, PostToolUse | 8/9 | 6/6 | 29.46 s | 701,446 | 7/9 |
| Safety + review hooks | PreToolUse, PostToolUse | 9/9 | 6/6 | 33.29 s | 849,795 | 9/9 |

The full-hook profile had one `retry_review` run that failed its visible check and patch rubric. No post-test edits were recorded. Paired median time changed by +0.75 s (95% bootstrap CI -5.45 to +7.14) with all hooks, and +2.93 s (-1.84 to +18.44) without `SessionStart`. Paired token change was +326 (-15,855 to +17,457) and +17,469 (+16,476 to +33,651), respectively. The PreToolUse+PostToolUse profile therefore used more tokens in this screen; neither profile showed a reliable speed gain. The review action appeared in 7/9 full-hook runs and 9/9 PreToolUse+PostToolUse runs, versus 0/9 baseline runs. The successful-test hint was unconditional in these trials; post-test guidance is now available only by opt-in. The separate injected-defect screen above found no correction, so these actions do not establish review benefit. No trial invoked MCP or the MLX model. API-equivalent estimates were $0.0156 baseline, $0.0173 full hooks, and $0.0188 PreToolUse+PostToolUse; these are not Codex bills. Raw runs: [`codex-hook-event-followup.json`](codex-hook-event-followup.json). Summary: [`codex-hook-event-followup-summary.json`](codex-hook-event-followup-summary.json).

## PreToolUse-only follow-up

To separate the safety hook from the post-test review hint, three eligible coding tasks ran two matched repetitions with baseline and a PreToolUse-only profile (12 runs). Every run-level pre/post isolation audit passed. Baseline had no hooks or MCP servers; the hook profile manifest had one cam-laya-mcp `PreToolUse` command, no MCP servers, and no other hook commands. All visible checks passed (6/6 per profile); all applicable edge checks passed (4/4 per profile). Neither profile prompted a post-test `git diff` or recorded an edit. Laya recorded no policy decisions and Codex made no MCP calls.

| Profile | Runs | Quality | Median elapsed | Total tokens | API-equivalent estimate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 6 | 6/6 | 26.565 s | 488,086 | $0.01082 |
| PreToolUse only | 6 | 6/6 | 27.240 s | 438,654 | $0.00996 |

Paired median time changed by +1.14 s (95% bootstrap CI -9.12 to +8.255); paired total tokens changed by -156 (-25,241.5 to +681.5). Both intervals include zero. This small screen shows no reliable speed or token gain. API-equivalent estimates are not Codex bills. Raw runs: [`codex-hook-pre-only-followup.json`](codex-hook-pre-only-followup.json). Summary: [`codex-hook-pre-only-followup-summary.json`](codex-hook-pre-only-followup-summary.json).

## PostToolUse registration with guidance disabled

An exploratory three-pair screen kept PreToolUse and PostToolUse registered while disabling the successful-test hint. All six pre-run and post-run audits passed; visible checks passed 3/3 per profile, applicable edge checks passed 2/2, and there were no MCP calls, Laya decisions, review hints, or post-test edits. Despite the silent handler, paired median time changed by +10.48 s (95% bootstrap CI +2.44 to +12.47) and total tokens by +16,491 (+16,459 to +49,038). This is one run per task, so it does not establish the cause; alongside the PreToolUse-only screen, it suggests the PostToolUse registration itself adds overhead. Default Codex and Claude setup now registers only SessionStart and PreToolUse. Set `post_test_guidance = true` and rerun setup to opt in to PostToolUse. Raw runs: [`codex-post-event-no-guidance-check.json`](codex-post-event-no-guidance-check.json). Summary: [`codex-post-event-no-guidance-summary.json`](codex-post-event-no-guidance-summary.json).

## Default Codex install profile follow-up

A six-pair exploratory screen compared baseline with the current default profile (SessionStart + PreToolUse). Isolation audits passed: baseline had zero hooks/MCP, and the hook profile contained only cam-laya-mcp hooks with no other MCP servers or calls.

- Quality passed 5/6 baseline runs and 6/6 default-profile runs. The baseline `retry_review` miss was not linked to a Laya decision; this small screen does not demonstrate a quality benefit.
- Paired median elapsed-time change was +0.455 s (95% CI −4.55 to +8.59); paired median total-token change was −11 (95% CI −24,249.5 to +24,529). Both intervals cross zero, so this screen shows no reliable speed or cost effect.
- Raw data: `docs/codex-default-profile-followup.json`; summary: `docs/codex-default-profile-followup-summary.json`.

## Direct hook startup microbench

Thirty fresh invocations per event used the managed Python 3.12.14 executable in randomized order, with temporary config/state and a dirty tracked file. Median process time was 47.48 ms for `SessionStart`, 47.25 ms for a safe `PreToolUse` command, and 59.15 ms for the deterministic post-test review path. The run made no Codex or MCP calls and loaded no MLX model. This puts the default no-preload `SessionStart` cost near 50 ms per Codex session; the paired task screen did not show that dropping it improves end-to-end performance, so keep the registration as-is. Details: [`codex-hook-startup-microbench.json`](codex-hook-startup-microbench.json).
