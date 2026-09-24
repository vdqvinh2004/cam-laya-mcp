# Feature specification: Local Laya-MLX decisions

## Goal

After one setup, supported coding agents use Laya-MLX locally for selected small typed decisions while their coding LLM keeps reasoning and code generation.

## User scenarios

1. On Apple Silicon, `cam-laya-mcp setup` checks the environment and asks before installing missing Laya-MLX. Once approved it creates an isolated runtime, downloads the verified default checkpoint through Laya-MLX, runs an inference, and installs available client adapters.
2. On session start, native hooks/plugins start one local process. The model loads on the first useful decision or when preload is configured. Normal coding continues if the runtime is unavailable.
3. A dangerous tool action is blocked by a deterministic rule. Model confidence cannot bypass it.
4. An agent can call seven compact MCP tools when its own workflow makes that useful. MCP registration alone makes no promise of automatic calls.
5. A repeated decision can be served from a bounded in-memory cache. Short task requests without secret markers and strictly shaped push commands use digest keys; arbitrary commands remain uncached. Task changes, repository metadata changes, config changes, and model changes invalidate relevant entries.
6. `doctor`, `benchmark`, `stats`, `disable`, and `uninstall` report or change only this integration.

## Acceptance

- Typed `choice` inference uses current `laya_mlx.load(...).predict(...)` and the published MLX checkpoint.
- No PyTorch or cloud inference dependency.
- Codex/Claude native hooks and OpenCode plugin automatically handle supported events.
- Existing client settings survive setup; owned entries alone are removed.
- Missing model or failed inference yields normal agent workflow except hard rules and configured mandatory safety checks.
- Codex and Claude hooks can provide test and review hints before commit; OpenCode blocks risky actions and attaches post-test hints to the tool result. Ordinary tool results are skipped.
- Actual benchmark samples are reported; estimated savings are not invented.

## Constraints

- Apple Silicon, macOS 14+, Python 3.11+ for Laya-MLX. An isolated Python 3.12 runtime is used at installation.
- All model input stays local. Small whitelisted state only; no source files or whole conversations.
- Codex user hooks require Codex trust review before they execute.

## Milestone 5: Measurable agent efficiency

The Milestone 4 Codex comparison showed higher token use and response time with Laya enabled. Milestone 5 must test whether selective local decisions improve a real coding workflow. A decision count or cache hit alone is not a benefit.

### User story 1 (P1): Trustworthy measurement

As a maintainer, I can see where a Codex task spends time and tokens, compare identical coding tasks with and without Laya, and tell actual quality from a marker match.

**Independent acceptance:** At least six representative tasks use disposable identical checkouts, executable checks, and a patch-quality rubric. Paired trials are repeated with counterbalanced order. Results show input, cached input, output, wall time, time to first useful response, tool/hook calls, cold and warm model timings, quality, and failures. Billed cost remains unavailable unless a bill is actually captured; any public-rate estimate is labeled separately.

### User story 2 (P1): Decisions only when useful

As a Codex user, simple work proceeds without waiting for a cold local model. The agent can request a typed route decision through MCP when the task state changes.

**Independent acceptance:** MCP owns task routing; prompt hooks do not infer automatically. Cached decisions invalidate on task, repository, config, or model change. Deterministic and low-value paths bypass inference. Hard risk and mandatory-safety behavior stay intact.

### User story 3 (P2): Demonstrated net benefit

As a maintainer, I ship an enabled policy only when it improves an eligible task cohort without reducing correctness or safety. Otherwise the policy stays disabled by default and the report says why.

**Independent acceptance:** Labeled ambiguous decisions beat a simple deterministic baseline before they enter the agent path. The selected integration is compared with no Laya on the same task set. A benefit claim requires no quality regression, no hard-safety regression, and a repeatable reduction in total Codex tokens and elapsed time for eligible tasks; report overall and bypass-task results as well. Publish per-task variance and the raw aggregate metrics.

### Milestone 6 experiment (not shipped): Retrieve repository context

Hypothesis: a deterministic local MCP search can return relevant source and test locations for tasks with hidden target paths and reduce agent search effort.

Outcome: Codex made zero retrieval calls across four discovery pilots, including after one stronger tool-use instruction. The adoption gate failed; the prototype was removed and no efficiency claim is supported. Details and pilot data are in `milestone-6-research.md` and `docs/codex-efficacy-baseline.md`.
