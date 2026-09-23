# cam-laya-mcp

Small local decisions for coding agents, powered by [Laya-MLX](https://github.com/mizorewww/laya-mlx). Your coding LLM still reads the repository, reasons, writes code, and explains changes. Laya-MLX chooses among short options for selected workflow transitions. It uses MLX on Apple Silicon, with no Laya cloud account, API key, or PyTorch runtime.

## Quickstart

Requires Apple Silicon, macOS 14+, Python 3.11+, and [uv](https://docs.astral.sh/uv/getting-started/installation/). On macOS with Homebrew, install uv with `brew install uv` if needed.

```sh
git clone https://github.com/vdqvinh2004/cam-laya-mcp.git
cd cam-laya-mcp
uv tool install -e .
cam-laya-mcp setup
cam-laya-mcp doctor
```

Setup asks before installing missing Laya-MLX. After approval, it creates an isolated Python 3.12 runtime, downloads the checkpoint, runs a smoke decision, and configures detected Codex, Claude Code, and OpenCode installations. Then open your usual coding agent and work normally; no per-session Laya command is needed. Run `cam-laya-mcp test` for another smoke check or `cam-laya-mcp benchmark` for local timings. Running setup again is safe.

Already have the source checkout? Start at `cd cam-laya-mcp`. `cam-laya-mcp setup --yes` is only for automation where installation was already approved.

The earlier `laya-agent` command remains an alias. Existing MCP entries and local config/state paths keep that name so upgrades preserve working installations.

The default checkpoint is `aac6fef/laya-mlx`, the published English MLX checkpoint in the current Laya-MLX README. Hugging Face stores it under `~/.cache/huggingface/hub/models--aac6fef--laya-mlx` by default. The upstream repository does not state a fixed disk or memory requirement for every device; run `cam-laya-mcp doctor` and `cam-laya-mcp benchmark` on your machine. First download needs internet; inference after download is local.

To inspect checkpoint files and resident memory on your Mac, run `du -shL ~/.cache/huggingface/hub/models--aac6fef--laya-mlx` and `ps -o rss= -p "$(cat ~/.local/state/laya-agent/agent.pid)"` after a decision. `du -L` follows cache links; RSS is reported in KiB and includes the process beyond model weights.

## Automatic use

| Client | Integration | Automatic events | Caveat |
| --- | --- | --- | --- |
| Codex | stdio MCP + user hooks | session start, user prompt, pre/post tool | Codex requires one-time `/hooks` trust review for new user hooks. |
| Claude Code | stdio MCP + user hooks | session start, user prompt, pre/post tool | Hooks run only when Claude Code loads user settings. |
| OpenCode | local MCP + JS plugin | session creation, pre/post tool | The documented plugin API has no user-prompt event. |
| Other MCP clients | stdio MCP | none guaranteed | Their agent must choose when to call a tool. |

Hooks start one on-demand Unix socket process. The model loads on the first useful decision, or at session start when `preload = true`. MCP tools use that same process. Normal read, edit, and test work does not call Laya every time. Prompt routing applies only to short task-like prompts; pre-tool model checks apply to selected ambiguous commands; hard rules block dangerous commands without model inference. A failed test gets a deterministic debug routing hint. A pre-commit transition may ask for a local review decision.

Codex may show a hook trust notice after setup. Run `/hooks`, inspect the installed `laya-agent` definitions, and trust them. Until then, Codex skips those hooks. MCP registration alone never guarantees automatic tool calls.

For dangerous commands, Claude Code's hook requests a native approval. Codex currently documents `ask` as unsupported for PreToolUse hooks, so its hook denies the command; the user can run an approved command manually. OpenCode's plugin stops the command with an error and likewise requires a manual action. These client limits are not hidden by the MCP integration.

OpenCode may use `OPENCODE_CONFIG_DIR` for its active configuration, including embedded integrations. Setup configures both that directory and the default user directory when they differ; `opencode debug paths` shows the active path.

## Example

User says “Fix the checkout bug.” The coding LLM inspects the repository and writes the patch. The prompt hook may classify `debugging`. Before a risky command, the hard policy can block it. A failed `npm test` produces a short `debug` hint. Before commit, Laya may choose `self_review` or `run_tests`. The LLM still does the actual debugging, testing, and review.

MCP tools: `laya_status`, `laya_decide`, `laya_route_task`, `laya_risk_check`, `laya_next_action`, `laya_test_decision`, and `laya_review_decision`. All responses are small JSON objects. A generic stdio MCP entry runs `cam-laya-mcp mcp`.

For another MCP client, use its documented stdio server configuration with command `/absolute/path/to/cam-laya-mcp` and argument `mcp`. Generic MCP setup exposes tools but cannot guarantee automatic invocation; use the client's own lifecycle mechanism when it has one.

## Commands

```sh
cam-laya-mcp status       # compact availability and warm-model state
cam-laya-mcp doctor       # environment, cache, MCP, and client checks
cam-laya-mcp test         # actual local smoke inference
cam-laya-mcp benchmark    # measured load, inference, cache timing
cam-laya-mcp stats        # local counts and explicitly estimated savings
cam-laya-mcp configure    # prints config path
cam-laya-mcp disable
cam-laya-mcp enable
cam-laya-mcp uninstall
```

`uninstall` removes only integration entries created by this tool. Optional `--remove-runtime`, `--remove-model-cache`, and `--remove-config` remove those items separately. The model cache may be shared with other tools, so it stays by default. Existing client settings are merged and backed up to `.laya-agent.bak` files. OpenCode `.jsonc` comments are retained in the backup; the active file is rewritten as valid JSON.

User config: `~/.config/laya-agent/config.toml`. State and a local Unix socket: `~/.local/state/laya-agent/`. No prompt, command, source file, or credential value is written to the stats file. The model receives whitelisted short state facts, a short task or selected command when needed, and fixed choice labels. It receives no full conversation or repository source. Model failure returns `defer_to_agent`; deterministic dangerous-action rules continue to apply. Confidence is a routing hint, never permission.

`stats` reports local decision counts, cache hits, model failures, and latency. Savings remain zero unless a caller explicitly supplies `would_call_llm: true` for a decision that would otherwise need its own LLM call. The caller may also supply `estimated_llm_tokens`; these are counted under `estimated_tokens_saved`, never as exact usage. A count of Laya decisions is not a count of LLM calls avoided. `benchmark` samples the local machine; upstream published numbers are not reused as local results.

Laya-MLX 0.2 warns that the published checkpoint has an uncalibrated `choice:11+` temperature bucket. Task routing uses 12 labels, so `laya_route_task` returns `reason_code: confidence_uncalibrated` and does not use that confidence for threshold-based escalation. Other policies use at most ten labels.

## Troubleshooting

- `doctor` says unsupported: check Apple Silicon, macOS 14+, Python 3.11+. The coding agent keeps working without Laya.
- Model missing: rerun `setup` on a network connection. The checkpoint is downloaded by Laya-MLX on first load.
- Codex hooks skipped: inspect `/hooks` and trust the exact installed definitions.
- MCP unavailable: run `cam-laya-mcp doctor`, then rerun `setup`; existing unrelated MCP entries are preserved.
- Model failure: run `cam-laya-mcp test` for a smoke check, then `benchmark` only after it passes.

## Development

```sh
uv sync --extra test
uv run pytest -q
```

Source-backed client capability choices and limits are in [ADR 0001](docs/adr/0001-local-decision-layer.md). The Spec Kit feature documents are in [specs/001-cam-laya-mcp](specs/001-cam-laya-mcp/spec.md).
