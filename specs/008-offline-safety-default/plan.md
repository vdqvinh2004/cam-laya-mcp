# Implementation Plan: Offline Safety Default

**Branch**: `008-offline-safety-default` | **Date**: 2026-09-28 | **Spec**: [spec.md](spec.md)

## Summary

Make deterministic command and sensitive-file protection the default product path. A normal setup installs usable native hooks without Apple Silicon, MLX, a checkpoint, or model startup. Preserve the existing local Laya-MLX decision service as an explicit experiment, keep upgrades ownership-safe, and prove guard accuracy and overhead before any broader claim.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Standard library for the guard; existing `json5` for OpenCode config; `mcp` and `laya-mlx` retained for explicit model/MCP installations  
**Storage**: Existing user config, owned-integration manifest, and bounded private state files; no new database  
**Testing**: pytest, MCP stdio roundtrip for model mode, isolated client profiles, command corpus, local subprocess latency benchmark, paired Codex task screen  
**Target Platform**: Guard on macOS and Linux; optional MLX on supported Apple Silicon macOS; Windows deferred  
**Project Type**: Python CLI with native client hooks and optional stdio MCP service  
**Performance Goals**: Guard-only hook process p95 at most 60 ms on the reference Mac, compared with measured 104.9 ms baseline  
**Constraints**: No raw command/prompt/source in persistent logs; no default model download or daemon startup; preserve unowned client settings; no claim of complete shell isolation  
**Scale/Scope**: Three client adapters, one shared safety policy, one optional model runtime; no new inference provider

## Constitution Check

| Principle | Decision |
| --- | --- |
| Local MLX only | Pass: MLX remains the sole model decision runtime and requires explicit setup. No cloud or PyTorch fallback. |
| Coding agent owns reasoning | Pass: hooks gate known-risk actions; they do not write code or take over task reasoning. |
| Safety outranks model | Pass: deterministic checks run before optional model calls and cannot be overridden. |
| Automatic where real | Pass: only native hooks/plugins claim automatic enforcement; MCP stays opt-in and advisory. |
| Small and private | Pass: reuse existing adapters and config paths, avoid a new daemon for guard calls, retain metadata-only logs. |

No constitution amendment is needed. Recheck these gates after the contract and migration design.

## Project Structure

```text
specs/008-offline-safety-default/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── cli.md
│   └── hooks.md
├── quickstart.md
├── checklists/requirements.md
└── tasks.md

src/laya_agent/
├── cli.py             # setup modes, diagnostics, fast hook entry
├── hooks.py           # native event handling
├── policy.py          # shared deterministic risk and optional decisions
├── integrations.py    # owned client entries
├── config.py          # compatible user preferences
├── runtime.py         # optional Apple Silicon MLX path
├── daemon.py          # optional model service
└── mcp_server.py      # optional typed decision tools
tests/
├── test_core.py
├── test_integrations.py
└── test_mcp_roundtrip.py
```

**Structure decision**: Evolve the existing package. Reuse the policy and adapters; move imports behind CLI branches where needed for speed. Do not rename the command, config paths, or MCP tool names in this milestone.

## Design and Delivery

### Phase 0: Evidence and capability boundary

Use [research.md](research.md) as the baseline. Freeze a labeled risk corpus before changing the scanner. Record safe-hook process latency and the current default setup failure on a host without MLX. Verify which client events can deny, request approval, or only advise; mark absent binaries unverified.

### Phase 1: Guard-only MVP

Add `setup --guard-only` as the candidate path while the existing default remains available during evaluation. It writes config, then installs detected native safety integrations without calling the model platform gate, creating an MLX runtime, requiring `uv`, or invoking `test`. Keep hard rules before all optional inference. Avoid a daemon request for routine safe actions. Register no advisory MCP server or extra hook event in a new guard-only profile. This phase is independently useful and can ship if later optional-model work pauses.

### Phase 2: Upgrade and model opt-in

Add `setup --with-model`; keep legacy `setup --yes` as an explicit noninteractive model-setup alias for existing automation. Run model-specific platform check, isolated runtime install, and checkpoint smoke only after explicit model setup or approval. Preserve `enabled = true` on upgrade and keep owned MCP registration when its runtime is healthy; if an existing user's model runtime is missing, report how to repair it without silently changing their preference. If optional model setup fails, leave guard integration in place and report the failure. Make `enable` verify model readiness before changing config; `disable` affects model advice only. Preserve owned-entry and JSONC behavior.

### Phase 3: Status and client proof

Report guard installation, observed hook execution, trust-review limits, and optional MLX readiness separately. Do not equate configured hooks with trusted/live hooks. Add isolated real-client safe-pass and dangerous-block trials where binaries and credentials are available. Keep claims for unavailable Claude Code or untrusted live profiles explicitly unverified.

### Phase 4: Release gate and cleanup

Run the locked and holdout command corpora, installation migration matrix, fast-hook benchmark, paired benign coding screen, full tests, build, and read-only doctor. If the gates pass, make guard-only the default `setup` behavior and rerun clean-room validation on that exact command. Split default versus optional Python dependencies only if the clean-room guard path still imports an optional package or the package footprint materially harms setup. Remove dead default advice plumbing only after compatibility tests pass; retain the opt-in experiment. Update README, release readiness, and the milestone index with measured results, including failures.

## Release Gate

Milestone 8 ships the new default only if all SC-001 through SC-006 in [spec.md](spec.md) pass. In particular: every locked and held-out covered destructive case stops; at least 99/100 benign cases proceed; p95 guard-only process time is at most 60 ms on the reference Mac; client ownership tests have zero unowned mutations; and benign paired tasks have no quality loss and less than 5% median time/token increase. A failed gate leaves the existing default in place and records the negative result. No speed or cost claim follows from a faster hook alone.

## Risks and rollback

- Static command inspection is not a sandbox. Document uncovered dynamic scripts and avoid a comprehensive-protection claim.
- Clients differ in review behavior. Codex/OpenCode may deny and require manual execution; Claude can request native approval. Verify actual client responses before naming them supported.
- A partial setup must leave previously installed safety hooks usable. Retry and uninstall only manifest-owned entries; preserve backups and unowned settings.
- Existing model users must not be silently downgraded. If migration cannot preserve their mode, stop and repair the migration before changing the default.

## Post-design Constitution Check

Pass. Contracts keep MLX local and optional, guard decisions deterministic, client behavior capability-specific, and persistent data free of raw actions. The plan adds no second model runtime, code-generation engine, or unverified automatic MCP claim.

## Implementation evidence — 2026-09-28

- Plain `setup` clean room passed on the reference Mac and in Ubuntu 24.04: repeat setup, safe and destructive hooks, and uninstall with fake client binaries and temporary homes. No `uv`, checkpoint, daemon socket, or MCP entry was used. The hosted GitHub Actions job is configured but awaits a pushed commit.
- Locked and holdout corpus: L 112/112, B 113/113, H 35/35, G 39/39. Final whole-process 100-hook Mac run: median 37.44 ms, p95 41.09 ms, maximum 43.11 ms; zero daemon starts and safe denials. Ubuntu container p95 was 46.08 ms over 20 samples.
- Live Codex trial in an isolated profile: one safe hook pass and one destructive deny; the disposable target remained. Claude Code was unavailable. OpenCode's isolated authentication check timed out, so its live execution is unverified.
- Six benign coding tasks × three matched pairs: 18/18 independent checks for baseline and guard, 75 actual guard hook calls, zero MCP calls; median paired time −3.88% and tokens −1.07%. An earlier network-disrupted screen was discarded. This satisfies nonregression, not the separate productivity-claim gate.
- Final local checks: Mac `uv run pytest -q` 104 passed; Ubuntu container 104 passed; typed MCP roundtrip 1 passed; `cam-laya-mcp test` returned `inspect` on Apple Silicon; evaluator self-check passed; `uv build` made wheel and sdist; read-only `doctor` left inspected live configs unchanged. Plain `setup` was switched to guard-only after these gates passed.
