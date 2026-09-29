# Milestone 8 research: offline safety default

## Evidence

- `src/laya_agent/cli.py:setup` rejects hosts outside Apple Silicon/macOS and requires a Laya-MLX smoke test before installing any detected client. `Config.enabled` is false by default. The deterministic `hard_risk` path in `hooks.py:run` already runs before model inference.
- The corrected isolated Codex screen showed no reliable speed gain. PreToolUse+PostToolUse added 17,469 paired median tokens (95% CI +16,476 to +33,651); billed cost was not observed. A 12-state screen scored deterministic rules 12/12 and raw Laya choices 4/12. See `docs/release-readiness.md` and `README.md`.
- Milestone 6's retrieval prototype received zero Codex calls across four discovery trials, including after changed guidance, and was removed. MCP registration alone did not cause useful work.
- Active Codex hooks/MCP and OpenCode MCP are disconnected on the current Mac; Claude Code is absent. Disposable profile tests exist, but live trust and client execution remain unverified (`docs/release-readiness.md`).
- A fresh 2026-09-28 local process benchmark called `.venv/bin/cam-laya-mcp hook codex PreToolUse` 30 times with `git status`: median 100.8 ms, p95 104.9 ms, maximum 285.9 ms. This is CLI process plus hook time on one Mac, not measured Codex task overhead.

## Decisions

### Default setup installs the guard first

**Decision:** Remove model-platform and checkpoint prerequisites from default setup. Install native pre-tool safety hooks with the already installed CLI on macOS and Linux. Do not register advisory MCP tools by default.

**Rationale:** The default model is off, while known dangerous actions can already be checked locally. This makes the useful path available without MLX download or agent tool adoption.

**Alternatives:** Another MLX prompt or retrieval tool has weak accuracy/adoption evidence. Removing Laya-MLX entirely would break existing users and offers no additional safety benefit for this milestone.

### Keep MLX explicit and compatible

**Decision:** `setup --with-model` retains isolated-runtime installation, smoke testing, and owned MCP registration on supported Apple Silicon. Existing `enabled = true` remains the user's model preference; setup must preserve it. `enable`/`disable` continue to control model advice only.

**Rationale:** Separates safety from the experiment without renaming CLI aliases or config/state paths. Optional model failures cannot cancel a usable guard installation.

**Alternatives:** Making MLX mandatory repeats the current setup barrier. Replacing it with a cloud model violates the local-runtime principle.

### Reuse the current integration owners

**Decision:** Extend current Codex, Claude Code, and OpenCode adapters to choose guard-only or guard-plus-model entries. Keep manifest ownership, backups, and JSONC preservation. Do not create another installer framework.

**Rationale:** Existing adapters and tests cover the hard migration cases; replacing them adds risk without user value.

### Make the hook process lighter

**Decision:** Keep the deterministic path synchronous and local; defer CLI imports used only by setup, daemon, MCP, benchmarks, and model inference. Measure end-to-end hook process time rather than only `hard_risk` time.

**Rationale:** Current safe hook process p95 is 105 ms. A direct, lazy-import path can reduce common-call cost without adding a service.

**Alternative:** A persistent guard daemon could save process startup but adds lifecycle and failure modes; try import reduction first.

### Verify narrow safety claims

**Decision:** Freeze a labeled corpus of covered destructive and benign actions, add unseen holdout cases, and test client hook responses. Keep a static scanner; use a shell parser dependency only if the corpus exposes a failure that cannot be fixed safely with the current checks.

**Rationale:** Static inspection cannot guarantee what a dynamic shell script will execute. Quality is defined by explicit risk families, false blocks, and honest limits, not a sandbox claim.

## Open platform boundary

macOS and Linux are the first guard targets. Windows needs tested client command quoting, config paths, and process behavior, so it is outside Milestone 8 support claims. Laya-MLX remains Apple Silicon/macOS only. Client trust review may require a user action; installed configuration is not proof of execution.
