# Milestone 5 research: Codex efficacy

## Observed baseline

The 2026-09-24 paired run in `docs/codex-efficacy-results.json` covered five short prompts once each. Laya raised total Codex tokens from 147,142 to 184,269 (+25.2%) and median wall time from 17.91 s to 23.87 s (+33.3%). The extra tokens were concentrated in `review_hint` (+19,117) and `cache_repeat` (+16,864). All marker checks passed, but no task edited code or ran a verification command. Billed USD was unavailable. These observations establish a regression for this task set, not the cause of every extra token.

## Code and measurement findings

1. `hooks.py:UserPromptSubmit` calls `task_changed`, which clears the daemon cache, then asks for `route_task`. `mcp_server.py` tells Codex to call `laya_route_task` at task start. In the repeated-task run, this produced three route requests (one hook, two MCP) and one cache hit. The hook and MCP calls can carry different state, so identical user requests need not share a cache key.
2. `config.py` defaults `preload = false`. `Runtime.predict` loads the model synchronously on first inference. Hook decisions use a 5 s daemon timeout; MCP decisions use 60 s. The daemon serializes decisions behind `metrics_lock`. `daemon.request` catches socket timeouts as generic `OSError` and retries up to 20 times, potentially resending an expensive decision. Cold load, inference, queue wait, and timeouts are not separately reported, so the recorded 7.5–37 s cumulative average model latencies cannot identify the exact bottleneck.
3. `DecisionEngine.should_call_laya` defers ordinary decisions after its recent model latency exceeds 500 ms, but callers still pay their hook/MCP round trip. The latency gate cannot recover because deferred calls add no new latency samples. The event log writes the last inference latency even for a later deterministic or cached decision; the benchmark reads a cumulative average rather than a per-run latency delta.
4. Seven MCP tools and server instructions are exposed together. The benchmark's `failed_test`, `review_hint`, and `cache_repeat` prompts explicitly request MCP calls; `quality_ok` checks a word marker and call count. `review_hint` passed despite a `low_confidence` Laya outcome. Baseline always runs before enabled, and there is one pair per task. `read_stats` can start the daemon before the timed Codex interval, excluding startup. This setup cannot establish code quality, token source, variance, or a real workflow benefit.
5. Hard risk rules and mandatory safety are independent of model confidence. Cache keys are digests and arbitrary secret-bearing text is excluded. Optimization must preserve those boundaries.
6. Cached input was 115,456 tokens baseline and 150,784 with Laya; uncached input was 30,969 and 32,872. At the published 2026-09-24 `gpt-6-luna` Standard short-context API rates ($0.10 input, $0.01 cached input, $0.50 output per million), the API-equivalent totals would be about $0.00461 and $0.00510 (+10.7%). This is a pricing illustration, not the user's Codex bill; the trial exposed no billed USD.

## Decisions and alternatives

- **Fix timeout handling first.** Retry only connection/startup failures, not an established request that timed out; preserve fail-closed mandatory safety. A request ID can make any remaining retry idempotent.
- **Measure before pruning.** Add per-invocation timing and outcome fields, plus Codex event timing and token usage, then compare hook-only, MCP-only, combined, and no-Laya conditions. This separates startup, model, tool-call, and context overhead before changing the interface.
- **Use one useful decision per state.** Compare hook-owned and MCP-owned routing first. Remove automatic prompt routing if it only repeats a label Codex already knows. If both paths remain, deduplicate with a fingerprint that includes relevant task, repository, config, and model state; keep explicit MCP access for changed state. A shorter tool description alone cannot enforce this.
- **Gate by expected value.** Skip deterministic, trivial, stale, and cold decisions when their expected benefit cannot exceed measured delay; keep hard safety checks. Test scope selection and other ambiguous typed decisions are candidates only after a labeled decision set shows quality above simple rules.
- **Validate on coding work.** Use disposable, identical checkouts with actual edits and executable checks. Counterbalance condition order and repeat trials. A short prompt that asks Codex to call Laya tests tool availability, not agent efficiency.
- **Keep cost accounting honest.** Report input, cached input, output, wall time, and local model time separately. The [official OpenAI API pricing page](https://developers.openai.com/api/docs/pricing) publishes separate input, cached-input, and output rates. An API-equivalent estimate may use those rates with a dated source; it is not a Codex subscription bill or measured dollars saved.

## Open hypotheses to test

- Cold first inference and serialized MCP calls account for much of the long tail.
- Repeated tool turns, rather than static MCP registration alone, account for most extra Codex tokens.
- Selective typed guidance can save work on ambiguous test/review choices, while simple routing is unlikely to repay its overhead.

None of these hypotheses is yet a measured improvement.
