# Implementation plan

## Stack and boundaries

Python 3.11+ package, official `mcp` Python SDK, `laya-mlx` 0.2 API, standard library Unix sockets and JSON, and JSON5 only for OpenCode JSONC settings. Laya-MLX and MLX are installed into a separate Python 3.12 environment after explicit approval. No inference API key or PyTorch dependency.

## Architecture

`runtime.py` loads the published MLX checkpoint once; `policy.py` combines hard rules, typed choice decisions, selective digest-key caching, and mandatory-safety fallback; `context.py` compresses short project and task facts and derives a repository metadata revision. `daemon.py` shares warm model state between hook CLI calls and MCP requests, serializes decisions, and rotates local event logs. `mcp_server.py` exposes seven stdio tools. `integrations.py` owns client configuration and native hooks/plugins, including OpenCode's discovered live config source. `cli.py` handles setup, diagnostics, benchmark, and removal.

## Sequence

1. Check current upstream and official client APIs; record the capability matrix in ADR 0001.
2. Implement compact state, runtime, policy, and cache.
3. Add warm local process and MCP stdio server.
4. Add installer, CLI, client adapters, and automatic lifecycle handlers.
5. Verify hard safety, fallback, ownership, and MCP roundtrip with tests.
6. After approval, install Laya-MLX, run checkpoint smoke inference, then test detected real client configs.

## Verification

`uv run pytest -q`, `uvx ruff check --select F,I src tests`, `uv build`, `cam-laya-mcp test`, `cam-laya-mcp benchmark`, and `cam-laya-mcp doctor`. The final three require installed Laya-MLX for meaningful model results. Simulated daemon outages must fail closed when mandatory safety is enabled; end-to-end stdio tests cover stale sockets, concurrent requests, and event rotation.

See [ADR 0001](../../docs/adr/0001-local-decision-layer.md) for source-backed capability choices.

## Milestone 5: Measurable Codex efficiency

### Technical context and constitution check

Keep Python 3.11+, the installed Python 3.12 MLX runtime, stdlib daemon transport, and the existing MCP SDK. No new inference provider or dependency is needed. The agent still owns repository reasoning and code generation; Laya still chooses among small typed options. Safety rules remain authoritative, model input remains compact and local, and no raw prompt/source enters metrics. The milestone changes invocation and measurement, not those product boundaries. Research and tradeoffs are in `research.md`.

### Design

1. **Fix and instrument the path.** Stop retrying an established socket request after a response timeout; preserve mandatory-safety fallback. Assign a private invocation ID and record source, policy, outcome (`hard_rule`, `cache`, `model`, `defer`, `timeout`, `failure`), cold/warm flag, daemon startup, queue wait, model load, inference, and total hook/MCP time. Record only bounded timings and safe digests. Codex event collection records first useful response, total wall time including daemon startup, input/cached/output tokens, tool turns, checks, and errors. Keep run-specific counters rather than differencing a cumulative average.
2. **Isolate overhead.** Run the same short diagnostic prompts under no Laya, hooks only, MCP only, and both. Counterbalance order. This identifies registration/context, hook, MCP turn, and model costs. Do not use these prompts as evidence of coding benefit.
3. **Make invocation selective.** Compare hook-owned and MCP-owned routing in the diagnostic first. Remove automatic prompt inference if it adds only a redundant route label. If both paths remain, use shared safe task-state identity so a prompt hook and MCP request can reuse one result, while an unchanged task gets one agent-visible hint. Keep invalidation on changed request, repository metadata, config, and model. Move cheap hard rules and bypass decisions before any cold inference. Give the latency gate a recovery path, and do not block a prompt hook on a cold model when expected benefit is smaller than measured delay. Preserve explicit MCP decisions for changed or ambiguous state.
4. **Find a useful decision.** Build a small labeled corpus of compact ambiguous states for test scope/review/next action. Compare Laya choices with current hard rules and a simple deterministic baseline. Select a policy only if its advice changes an agent action safely and has enough accuracy to justify the round trip. Compare seven-tool MCP exposure with a smaller surface only if the diagnostic ablation implicates tool context or call choice.
5. **Confirm on real tasks.** Use at least six coding tasks spanning test selection, repeated bug fixing, review, configuration, and bypass. Give each condition a fresh disposable checkout at the same commit; allow edits and run task-specific checks. Run five paired trials per task for the selected design, reversing/randomizing order by pair and recording seed, model, checkout, conditions, and environment. Use executable checks plus a fixed patch rubric; blind human review may supplement, but a word marker cannot define success. Separate cold and warm cohorts. Stop early for safety or clear quality regression.

### Analysis and release gate

Report per-task paired differences and aggregate medians with a 95% paired bootstrap interval for total Codex tokens and elapsed time. Show p95 response time, first useful response, cached-token share, tool turns, local model time, and quality beside them. The target is at least 10% lower median tokens **and** elapsed time in the eligible cohort, with the paired intervals below zero, no lower task-check pass rate, and no safety regression. Report all-task and bypass results even if they miss the target. If no policy clears the gate, keep it disabled by default and publish the negative result. An API-equivalent dollar estimate may use dated published rates for uncached input, cached input, and output; it must be labeled separately from billed cost.

### Execution order

Timeout correctness and instrumentation precede diagnostic ablation. Route ownership and cold-path gating precede the labeled decision comparison. The selected policy and MCP surface precede the full paired validation. Update the efficacy report and close T028 only after that rerun. `data-model.md`, `contracts/milestone-5.md`, and `quickstart.md` define the compact records, interface behavior, and validation procedure.

## Milestone 6 outcome: deterministic context retrieval rejected

Milestone 5 failed its agent efficacy gate. Milestone 6 tested whether local search could save repository exploration when the target file is unknown. Codex did not use the tool in the pilot, including after one guidance adjustment, so the prototype was removed before a full paired run. No MLX dependency, model call, or automatic prompt hook was added. Evidence and pilot artifacts are in `milestone-6-research.md` and `docs/codex-efficacy-baseline.md`; the original contract and plan remain as a record of the rejected experiment.
