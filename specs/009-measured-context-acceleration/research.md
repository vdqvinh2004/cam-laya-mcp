# Milestone 9 Research: Measured Context Acceleration

## Decision

Test one opt-in, deterministic, native Codex prompt hint that names likely repository paths. Promote it only after live delivery and a task-level paired benefit. Keep guard-only as the baseline and model advice opt-in.

## Evidence

- [Milestone 5](../../docs/codex-efficacy-baseline.md) did not establish a model-advice gain. In the corrected screen, one hook profile used 17,469 more paired median tokens; billed spend was not measured.
- [Milestone 6](../006-agent-context-retrieval/research.md) showed useful lookup relevance on four fixtures, but Codex made zero calls to the optional MCP retrieval tool across four discovery trials, even after stronger guidance. More optional MCP description is unlikely to solve delivery.
- [Milestone 8](../../docs/release-readiness.md) reduced whole-process guard p95 from 104.9 to 41.09 ms. Its six-task, 18-pair screen passed all checks but showed only −3.88% median time and −1.07% tokens; it did not meet a productivity claim gate. The six tasks in `benchmarks/codex_coding_tasks.json` used for that screen name their target files.
- Official [Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks), fetched 2026-09-29, documents `UserPromptSubmit` input field `prompt` and `hookSpecificOutput.additionalContext` as extra developer context. It also documents trust review for non-managed hooks. Documentation supports a candidate delivery path; a disposable live trial is still required.
- Current `hooks.run()` returns `{}` for `UserPromptSubmit`, and `_hook_events()` does not register it for guard-only setup. The existing `PreToolUse` guard is independent of this candidate.

## Options considered

| Option | Decision | Reason |
| --- | --- | --- |
| More Laya prompt routing or post-test hints | Reject | Prior paired work found no reliable gain and sometimes higher token use. |
| Re-add optional MCP context retrieval | Reject | The previous tool was not called, so ranking quality alone cannot help. |
| Native prompt hook with bounded path hints | Test | Documented event can deliver context automatically before discovery; it can reuse local Git and stdlib. |
| Full semantic index, embeddings, or project rewrite | Defer | No observed bottleneck justifies index maintenance, dependencies, or model latency. |
| Do no performance work | Fallback | Correct if native delivery or paired efficacy fails; guard-only remains useful. |

## Method choices

- **Candidate**: At most three tracked paths with short neutral reasons, under 800 characters. Do not emit source text or commands to the agent.
- **Trigger**: Codex first; explicit experimental preference during study. An explicit target path or low-confidence result returns no hint.
- **Privacy**: Use prompt in memory only. Exclude sensitive/generated/vendor paths and symlink escapes; store only aggregate counts, timing, and opaque task IDs.
- **Pilot**: Use six separate tasks to prove live delivery, path relevance, bypass behavior, privacy, and quality. Allow one documented adjustment only on these tasks.
- **Main study**: Keep eight discovery and four bypass tasks from two pinned repos untouched until code freezes; run four matched pairs each with task-cluster intervals. No post hoc eligible-task selection.
- **Cost**: Token counts and published-price estimates are not billed charges. A billed-cost claim needs attributable provider records.

## Remaining risks handled by gates

The live Codex event may not deliver the documented context in this installed version; G0 stops work if so. Lexical path lookup may be irrelevant or slow in large repositories; G1–G2 stop or narrow it. A hint may still add more context than it saves; G3–G4 measure that at task level. OpenCode has no prompt event in the current integration, so this milestone makes no OpenCode efficacy claim.

## Milestone 8 baseline (T001 — 2026-09-29)

- Source revision: `7a08a23` (`feat: add deterministic hook guidance`); working tree dirty (modified README, benchmarks, release-readiness, milestone-1 specs, `src/laya_agent/*`, tests; untracked `.github/`, benchmark scripts, `docs/*paired*.json`, `docs/guard-*` evidence). No clean-commit baseline exists for rollout.
- Local evidence: guard corpus 299/299 pass; 100-sample whole-process hook p95 42.47 ms (median 40.23 ms, 0 daemon starts). 24-pair Codex guard screen (`baseline` vs `hooks_pre`, `gpt-6-sol`, low effort): 24/24 quality both profiles, paired time +0.205 s (95% CI −2.39 to +1.52), paired tokens −5.0 (CI −672 to +2,998); nonregression only, no productivity claim. Isolated live Codex safe-pass/destructive-deny passed; live OpenCode safe-pass/destructive-deny passed (first verification, `opencode-go/glm-5.3-flash`, ~$0.0028 billed); Claude Code blocked (binary absent).
- Hosted CI: `.github/workflows/test.yml` contains the Milestone 8 Ubuntu guard-only job, but no run was observed from this host (`gh` absent, no push performed). Status unverified.
- Release failures blocking Milestone 9 rollout: (1) hosted CI unverified — must pass before any default change; (2) dirty working tree — rollout needs a clean, tagged commit; (3) Codex billed cost unattributable per run — G5 cannot pass on Codex without billing records; (4) OpenCode has no documented prompt event and Claude Code has no live trial — no context support claim for either client.
