# Feature specification: Local Laya-MLX decisions

## Goal

After one setup, supported coding agents use Laya-MLX locally for selected small typed decisions while their coding LLM keeps reasoning and code generation.

## User scenarios

1. On Apple Silicon, `cam-laya-mcp setup` checks the environment and asks before installing missing Laya-MLX. Once approved it creates an isolated runtime, downloads the verified default checkpoint through Laya-MLX, runs an inference, and installs available client adapters.
2. On session start, native hooks/plugins start one local process. The model loads on the first useful decision or when preload is configured. Normal coding continues if the runtime is unavailable.
3. A dangerous tool action is blocked by a deterministic rule. Model confidence cannot bypass it.
4. An agent can call seven compact MCP tools when its own workflow makes that useful. MCP registration alone makes no promise of automatic calls.
5. A repeated decision can be served from a bounded in-memory cache. Free-form user tasks and arbitrary commands are excluded from cache fingerprints.
6. `doctor`, `benchmark`, `stats`, `disable`, and `uninstall` report or change only this integration.

## Acceptance

- Typed `choice` inference uses current `laya_mlx.load(...).predict(...)` and the published MLX checkpoint.
- No PyTorch or cloud inference dependency.
- Codex/Claude native hooks and OpenCode plugin automatically handle supported events.
- Existing client settings survive setup; owned entries alone are removed.
- Missing model or failed inference yields normal agent workflow except hard rules.
- Actual benchmark samples are reported; estimated savings are not invented.

## Constraints

- Apple Silicon, macOS 14+, Python 3.11+ for Laya-MLX. An isolated Python 3.12 runtime is used at installation.
- All model input stays local. Small whitelisted state only; no source files or whole conversations.
- Codex user hooks require Codex trust review before they execute.
