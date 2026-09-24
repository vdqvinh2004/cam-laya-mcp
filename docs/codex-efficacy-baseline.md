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

## Project decision

Pause active development. Across the completed evaluations, the current MCP advice pattern did not demonstrate agent performance or cost gains: the combined coding profile was 6,758 tokens lower in aggregate, but the paired token interval crossed zero, median elapsed time increased by 6.70 seconds, and agents made zero MCP calls and hook decisions during coding. The retrieval pilot also failed its adoption gate with zero tool calls across four discovery trials. Keep model inference disabled by default and retain deterministic risk checks. Resume performance work only when a client integration can reliably execute a useful action and a paired benchmark demonstrates net benefit.
