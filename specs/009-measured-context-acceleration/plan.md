# Implementation Plan: Measured Context Acceleration

**Branch**: `main` (planning only) | **Date**: 2026-09-29 | **Spec**: [spec.md](spec.md)

**Closeout (2026-09-29)**: G0 passed, G2 passed, G1 pilot failed (2/4 live discovery hits; 0/2 bypass correct; quality 5/6 vs 6/6). Main study skipped per stop rule. Candidate and prompt-hook registration removed; guard-only unchanged. No efficiency or billed-cost claim.

**Input**: Investigate and plan Milestone 9; do not implement it yet.

## Summary

Test one automatic, local, task-aware context hint for Codex discovery tasks. The current optional MCP retrieval pilot had relevant results but zero calls. Official [Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks) says `UserPromptSubmit` receives `prompt` and can return `hookSpecificOutput.additionalContext`; use that native path only after a disposable live delivery check. Keep Milestone 8 guard-only behavior and model preference intact. Build a representative paired study before deciding whether to ship the hint. A failed gate ends the experiment without a default change.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Existing standard library, Git, Codex CLI; no new runtime dependency or MLX call

**Storage**: Existing local config and owned client hook manifest; aggregate benchmark JSON only

**Testing**: pytest, existing guard corpus, real Codex hook trial, independent coding-task checks, paired bootstrap report

**Target Platform**: Codex on macOS first; Linux guard regression remains required; other clients only after separate verification

**Project Type**: Python CLI and native client hooks

**Performance Goals**: Context lookup p95 ≤250 ms; discovery-task paired median time and tokens each improve ≥10% with intervals below zero

**Constraints**: At most three paths and 800 characters per hint; local tracked files only; no raw prompt/source logs; existing guard decisions unaffected

**Scale/Scope**: Two pinned repositories, six pilot tasks plus 12 untouched main tasks, four matched pairs per main task

## Constitution Check

| Principle or gate | Design decision |
| --- | --- |
| Local MLX only | The new hint uses no model. Existing optional Laya-MLX remains the sole model runtime. |
| Agent owns reasoning | Output is neutral candidate paths, not instructions, generated code, or a forced edit. |
| Safety rules outrank model output | `PreToolUse` guard is untouched and its corpus must still pass. |
| Automatic where real | Codex's documented prompt hook is followed by a live receipt check; no claim for OpenCode or Claude Code without their own trial. |
| Small and private | Use bounded local lookup, no new index or dependency, no raw prompt/file-content logging. |
| Quality gates | Existing policy, config ownership, MCP roundtrip, model smoke where available, and packaging checks remain release gates. |

No constitution amendment is needed. Recheck these gates after any implementation and before rollout.

## Project Structure

### Documentation (this feature)

```text
specs/009-measured-context-acceleration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/context-hook.md
├── quickstart.md
├── tasks.md
└── checklists/requirements.md
```

### Source Code (repository root)

```text
src/laya_agent/context.py        # bounded tracked-path ranking; reuse existing context module
src/laya_agent/hooks.py          # UserPromptSubmit response; leave PreToolUse guard separate
src/laya_agent/integrations.py   # owned opt-in prompt-hook registration
src/laya_agent/config.py         # explicit context preference
src/laya_agent/cli.py            # setup and doctor state
benchmarks/evaluate_codex.py    # reuse hooks_pre baseline; add context profile and action observations
benchmarks/summarize_codex.py   # prespecified paired and task-cluster analysis
benchmarks/codex_coding_tasks.json # keep old screen frozen; add new corpus separately
tests/test_core.py
tests/test_integrations.py
```

**Structure Decision**: Reuse the existing hook, context, and benchmark paths. Add only a separate frozen Milestone 9 task manifest and evidence files. Do not revive an MCP retrieval tool, persistent index, or additional model service.

## Phase 0: Research and frozen decision rules

The [research](research.md) records why this candidate is the smallest plausible automatic intervention after Milestones 5–8. Before coding, verify the installed Codex version against official hook documentation, run a disposable `UserPromptSubmit` receipt trial, and freeze the candidate's payload, exclusions, pilot stop rule, task corpus, primary cohort, pair count, and statistical method. If the live hook cannot deliver context, stop without building retrieval.

Use at least two pinned repositories. Freeze six separate pilot tasks (four discovery, two bypass) and an untouched main set of eight hidden-target and four explicit-target/simple tasks. Each task needs an independent executable check and allowed patch scope. Tune lookup only on the pilot; make no changes after examining the main set. Avoid the current `bench_case` tasks as the sole evidence: those prompts name exact files and cannot establish discovery value.

## Phase 1: Design and pilot

The [data model](data-model.md) and [hook contract](contracts/context-hook.md) define the ephemeral path hint and observation fields. Use tracked filenames plus bounded local text matching; rank lexical matches, excluding secret, vendored, generated, and outside-root paths. Return no hint when explicit path or low confidence makes lookup unnecessary. No source excerpt, model call, cloud call, or persistent index.

Install the prompt event only for an explicit experimental preference in disposable profiles. Add a single focused test for ranking, privacy/bypass, hook response, and owned config changes. Run the existing 299-case guard corpus and isolated Codex pass/deny trial to prove no safety regression.

Pilot six separate tasks once per profile with counterbalanced order. Require live context delivery on every qualifying candidate run, all four hidden targets in the top three, zero hints on two bypass tasks, no leaked sensitive paths, and no candidate quality regression. Allow one documented lookup adjustment on the pilot only. Freeze code and tasks before opening the 12-task main set. If the pilot still fails, stop and remove or leave the candidate disabled.

## Phase 2: Whole-task study

Run four matched pairs per main task (48 pairs, 96 runs) in clean checkouts, reusing the existing `hooks_pre` profile as guard-only baseline and adding one `context` profile. Force model advice off in both. Keep model, reasoning effort, task wording, timeout, sandbox, and installed plugins equal. Counterbalance run order within each pair. Exclude only prespecified infrastructure failures; retain coding failures as quality failures. Record hook receipt, hint length, lookup time, first hinted-path use, discovery actions, time, input/output/cached tokens, independent check, patch scope, and safety outcomes. Never save full transcripts, prompts, or source in the evidence artifact.

Analyze the eight hidden-target tasks as the primary cohort with a paired, task-cluster bootstrap. Report the four bypass tasks separately. A rollout requires all spec success criteria, including ≥10% lower median paired time and tokens with both 95% intervals below zero and no quality regression. Report actual billed cost only if attributable provider billing is available; keep the current `api_equivalent_usd` estimate visibly labeled as a price estimate.

Estimate the 96-run time, tokens, and attributable spend from the pilot before starting the main study; record that spending decision with the frozen candidate.

## Phase 3: Decision and release

If the gate passes, expose the Codex context feature behind an explicit preference first, document its supported client and measured cohort, and decide any default change only after a normal trusted-profile trial. If the gate fails, remove the candidate, record the negative result, and preserve guard-only setup. Update release readiness, milestone index, and diagnostics to match observed behavior. Run the full suite, MCP stdio roundtrip, wheel/source build, `git diff --check`, and read-only doctor before closing.

## Decision gates

| Gate | Pass condition | Failure action |
| --- | --- | --- |
| G0 client delivery | Official contract and isolated live `UserPromptSubmit` context receipt | Stop candidate; document unsupported behavior. |
| G1 relevance/privacy | Pilot 4/4 discovery and 0/2 bypass; main ≥7/8 discovery and 0/4 bypass; zero unsafe paths | One pilot adjustment; no tuning on main tasks. Stop if still failing. |
| G2 safe overhead | Context lookup p95 ≤250 ms; Milestone 8 guard corpus and ≤60 ms p95 hook gate still pass | Optimize only measured cause or stop. |
| G3 coding quality | Both profiles ≥95% checks; candidate no worse across matched pairs; no new safety bypass | No rollout or efficiency claim. |
| G4 efficacy | Hidden-target time and tokens each improve ≥10%, paired task-cluster 95% intervals below zero; bypass median overhead ≤5% | Keep context disabled and publish negative result. |
| G5 cost | Actual attributable charges available and lower under paired analysis | Do not claim billed savings; token/time result can still be reported. |

## Complexity Tracking

No new framework, index, daemon, model route, or MCP tool is planned. The only new candidate behavior is one bounded local lookup on a verified prompt event. If that cannot meet the gate, delete it.
