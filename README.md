# cam-laya-mcp

Small local decisions for coding agents, powered by [Laya-MLX](https://github.com/mizorewww/laya-mlx). Your coding LLM still reads the repository, reasons, writes code, and explains changes. Laya-MLX chooses among short options for selected workflow transitions. It uses MLX on Apple Silicon, with no Laya cloud account, API key, or PyTorch runtime.

## Project status: experimental; productivity gate not met

The corrected isolated Codex screen tested three coding tasks across baseline, full-hook, and PreToolUse+PostToolUse profiles (27 runs). Checks passed 9/9, 8/9, and 9/9, respectively. Neither hook profile showed a reliable speed gain; PreToolUse+PostToolUse used 17,469 more paired median tokens (95% CI +16,476 to +33,651). A six-pair PreToolUse-only screen was inconclusive for time and tokens. Codex billed spend was not measured. See the [evaluation report](docs/codex-efficacy-baseline.md) and [release readiness](docs/release-readiness.md).

This remains an experiment for model advice, not a proven speed or cost optimization. A small 12-state screen favored deterministic rules (12/12) over raw Laya choices (4/12), so clear test/review transitions use those rules without model inference. The post-test hint increased `git diff` actions in the corrected screen (7/9 and 9/9 vs. 0/9 baseline), but a controlled Unicode-digit defect remained unfixed in all five hook trials. No post-test edits were recorded. Keep model decisions opt-in; do not claim productivity or cost gains. The guard-only default passed the [Milestone 8 local gates](docs/release-readiness.md), including one isolated live Codex safe-pass and destructive-deny trial. OpenCode live execution remains unverified; Claude Code is not installed.

Milestone 9 tested one automatic local path hint for Codex discovery tasks and stopped at its pilot gate: 2/4 live discovery targets in the top three (gate: 4/4), 0/2 bypass hints correct, quality 5/6 vs 6/6 guard-only. The candidate was removed; guard-only is unchanged and no efficiency or billed-cost claim follows. No OpenCode or Claude Code context support was attempted: OpenCode has no documented prompt event and Claude Code was not installed. See the [release readiness](docs/release-readiness.md) closeout.

## Quickstart

Default setup installs safety hooks on macOS or Linux with Python 3.11+. Once the package is installed, setup needs no Apple Silicon, MLX checkpoint, or `uv`:

```sh
cam-laya-mcp setup
cam-laya-mcp doctor
```

Optional model setup needs Apple Silicon, macOS 14+, Python 3.11+, and [uv](https://docs.astral.sh/uv/getting-started/installation/). On macOS with Homebrew, install uv with `brew install uv` if needed.

```sh
git clone https://github.com/vdqvinh2004/cam-laya-mcp.git
cd cam-laya-mcp
uv tool install -e .
cam-laya-mcp setup
cam-laya-mcp doctor
```

Plain `setup` installs owned PreToolUse safety hooks or the OpenCode pre-tool plugin. It adds no advisory MCP entry or session event for a new profile. `setup --guard-only` explicitly selects this mode. `setup --with-model` asks before installing missing Laya-MLX; `setup --with-model --yes` approves noninteractively. After approval, setup creates an isolated Python 3.12 runtime, downloads the checkpoint, runs a smoke decision, and adds owned MCP entries. Existing model-enabled profiles keep their preference and healthy owned access when setup is rerun. Model decisions remain disabled for new users. `enable` verifies the model first; `disable` leaves safety hooks active. Post-test guidance is off by default; set `post_test_guidance = true` in `~/.config/laya-agent/config.toml` and rerun setup to register PostToolUse hooks.

Already have the source checkout? Start at `cd cam-laya-mcp`. Legacy `cam-laya-mcp setup --yes` still means explicit noninteractive model setup for existing automation.

The earlier `laya-agent` command remains an alias. Setup migrates MCP entries it owns to `cam-laya-mcp`; local config/state paths keep their existing names so upgrades preserve data.

The default checkpoint is `aac6fef/laya-mlx`, the published English MLX checkpoint in the current Laya-MLX README. Hugging Face stores it under `~/.cache/huggingface/hub/models--aac6fef--laya-mlx` by default. The upstream repository does not state a fixed disk or memory requirement for every device; run `cam-laya-mcp doctor` and `cam-laya-mcp benchmark` on your machine. First download needs internet; inference after download is local.

To inspect checkpoint files and resident memory on your Mac, run `du -shL ~/.cache/huggingface/hub/models--aac6fef--laya-mlx` and `ps -o rss= -p "$(cat ~/.local/state/laya-agent/agent.pid)"` after a decision. `du -L` follows cache links; RSS is reported in KiB and includes the process beyond model weights.

## Automatic use

| Client | Integration | Automatic events | Caveat |
| --- | --- | --- | --- |
| Codex | user hooks; optional stdio MCP | pre-tool safety; model session and post-test events on opt-in | Codex requires one-time `/hooks` trust review for new user hooks. |
| Claude Code | user hooks; optional stdio MCP | pre-tool safety; model session and post-test events on opt-in | Hooks run only when Claude Code loads user settings. |
| OpenCode | JS plugin; optional local MCP | pre-tool safety; model session and post-test events on opt-in | The documented plugin API has no user-prompt event. |
| Other MCP clients | stdio MCP | none guaranteed | Their agent must choose when to call a tool. |

Guard-only hooks run locally without a daemon. With explicit model setup and `enable`, unresolved decisions may start the on-demand Unix socket process; `preload = true` can load the model at session start. Clear test/review transitions use small deterministic rules; MLX handles choices without a known rule. With `post_test_guidance = true`, failed tests get a debug hint and passing tests can get a self-review hint; these hints do not load MLX by themselves. Codex and Claude Code register PostToolUse only when this setting is enabled and setup is rerun. OpenCode can block risky actions before a tool call and append enabled post-test guidance to the tool result; its plugin API does not provide a reliable channel for a nonblocking precommit hint.

Codex may show a hook trust notice after setup. Run `/hooks`, inspect the installed `laya-agent` definitions, and trust them. Until then, Codex skips those hooks. MCP registration alone never guarantees automatic tool calls.

For dangerous commands, Claude Code's hook requests a native approval. Codex currently documents `ask` as unsupported for PreToolUse hooks, so its hook denies the command; the user can run an approved command manually. OpenCode's plugin stops the command with an error and likewise requires a manual action. These client limits are not hidden by the MCP integration.

Hard risk checks inspect shell commands across pipes, command separators, environment wrappers, command substitutions, and `sh -c` scripts. They cover recursive forced removal, force pushes, Git commands that discard local work, `find -delete`, input piped into a shell, infrastructure deletion, privileged changes, and secret paths. Simple quoted examples such as `echo 'rm -rf /tmp/data'` no longer trigger command rules. This is a conservative static check, not a shell sandbox: commands assembled dynamically or hidden in scripts still require the coding agent's own review.

OpenCode may use `OPENCODE_CONFIG_DIR` or another live config source, including embedded integrations. Setup configures that directory, the default user directory, and paths reported by `opencode debug config` when they differ. `opencode debug paths` shows its general directories; `opencode debug config` shows the source the running service loads.

## Example

User says “Fix the checkout bug.” The coding LLM inspects the repository and writes the patch. Before a risky command, the hard policy can block it. If the user enables post-test guidance, a failed `npm test` can produce a short `debug` hint. With model advice enabled, Laya can suggest `targeted_test` before commit. The LLM still does the debugging, testing, and review.

MCP server name: `cam-laya-mcp`. Tools: `laya_status`, `laya_decide`, `laya_route_task`, `laya_risk_check`, `laya_next_action`, `laya_test_decision`, and `laya_review_decision`. All responses are small JSON objects. A generic stdio MCP entry runs `cam-laya-mcp mcp`. Keep the stdio server open for repeated calls; it forwards decisions to a warm local daemon. Call decision tools when task state changes, using short facts. A decision is guidance, not permission.

The server advertises task-stage call guidance in MCP initialization instructions and individual tool descriptions. Agents choose whether to call tools; registration alone cannot force a call. Hooks invoke the same local daemon directly, so automatic hook activity does not appear as MCP tool calls. `cam-laya-mcp stats` reports `mcp_decisions` and `hook_decisions` separately. Restart an agent session after updating the installed server to load new MCP instructions.

For another MCP client, use its documented stdio server configuration with command `/absolute/path/to/cam-laya-mcp` and argument `mcp`. Generic MCP setup exposes tools but cannot guarantee automatic invocation; use the client's own lifecycle mechanism when it has one.

## Commands

```sh
cam-laya-mcp status       # compact availability and warm-model state
cam-laya-mcp setup                # default safety setup, no model setup
cam-laya-mcp setup --guard-only   # explicit safety-only setup
cam-laya-mcp setup --with-model   # explicit MLX setup and MCP registration
cam-laya-mcp doctor       # environment, cache, MCP, and client checks
cam-laya-mcp test         # actual local smoke inference
cam-laya-mcp benchmark    # measured load, inference, cache timing
cam-laya-mcp stats        # local counts and explicitly estimated savings
cam-laya-mcp configure    # prints config path
cam-laya-mcp disable
cam-laya-mcp enable
cam-laya-mcp uninstall
```

`uninstall` removes only integration entries created by this tool. Optional `--remove-runtime`, `--remove-model-cache`, and `--remove-config` remove those items separately. The model cache may be shared with other tools, so it stays by default. Existing client settings are merged and backed up to `.laya-agent.bak` files. OpenCode `.jsonc` comments remain in the active file, grouped above its rewritten JSON object.

User config: `~/.config/laya-agent/config.toml`. Set `post_test_guidance = true` and rerun setup to register successful-test review and failed-test debugging hints. State and a local Unix socket: `~/.local/state/laya-agent/`. No prompt, command, source file, or credential value is written to the stats file. The model receives whitelisted short state facts, a short task or selected command when needed, and fixed choice labels. It receives no full conversation or repository source. Ordinary model failure returns `defer_to_agent`; failed risk checks require human review when `mandatory_safety = true`, and deterministic hard rules always apply. Confidence is a routing hint, never permission.

`stats` reports decisions by policy and source, escalations, cache hits, model failures, and latency. The local event log keeps one 1 MB backup; it contains decision metadata, never raw prompts, commands, or source. Savings remain zero unless a caller explicitly supplies `would_call_llm: true` for a decision that would otherwise need its own LLM call. The caller may also supply `estimated_llm_tokens`; these are counted under `estimated_tokens_saved`, never as exact usage. A count of Laya decisions is not a count of LLM calls avoided. `benchmark` samples the local machine; upstream published numbers are not reused as local results.

Repeated short tasks without secret markers and strictly shaped `git push` actions can reuse an in-memory decision by digest. Arbitrary commands stay uncached. Hook-supplied repository state includes a digest of changed-file names and file metadata, so a file change invalidates those decisions without reading source content. This is a best-effort cache guard, not a credential detector; do not put secrets in MCP requests.

Laya-MLX 0.2 warns that the published checkpoint has an uncalibrated `choice:11+` temperature bucket. Task routing uses 12 labels, so `laya_route_task` returns `reason_code: confidence_uncalibrated` and does not use that confidence for threshold-based escalation. Other policies use at most ten labels.

## Troubleshooting

- `doctor` says model unsupported: guard-only safety still works on supported macOS and Linux with Python 3.11+. MLX needs Apple Silicon and macOS 14+.
- Model missing: run `setup --with-model` on a network connection. The checkpoint is downloaded by Laya-MLX on first load.
- Codex hooks skipped: inspect `/hooks` and trust the exact installed definitions.
- MCP unavailable after explicit model setup: run `cam-laya-mcp doctor`, then rerun `setup --with-model`; existing unrelated MCP entries are preserved.
- Model failure: run `cam-laya-mcp test` for a smoke check, then `benchmark` only after it passes.

## Development

```sh
uv sync --extra test
uv run pytest -q
```

Source-backed client capability choices and limits are in [ADR 0001](docs/adr/0001-local-decision-layer.md). The [v0.1.0 release audit](docs/release-readiness.md) records validation and open gates. [Spec Kit milestones](specs/README.md) keep each milestone's plan and tasks in its own numbered folder.
