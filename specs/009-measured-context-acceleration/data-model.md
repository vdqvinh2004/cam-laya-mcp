# Milestone 9 Data Model

These are planning records, not a new database or persistent index.

## Ephemeral context hint

| Field | Constraint |
| --- | --- |
| `eligible` | Boolean determined without a model; false for an explicit target or unsupported repository. |
| `paths` | Zero to three distinct, tracked, repository-local paths; no symlink escape, secrets, vendor, or generated paths. |
| `reasons` | One short, neutral reason per path; no source excerpt or user-prompt quote. |
| `text` | At most 800 characters; empty when ineligible, uncertain, or timed out. |
| `lookup_ms` | Local elapsed time, retained only as a numeric observation. |

Transient input is the client's `prompt` plus current repository state. The prompt and source contents are never stored in event or benchmark output.

## Coding task

| Field | Constraint |
| --- | --- |
| `task_id`, `repo_id`, `revision` | Stable anonymous IDs and pinned commit. |
| `set`, `cohort` | `pilot` (four discovery, two bypass) or untouched `main` (eight discovery, four bypass); frozen before tuning. |
| `prompt`, `target_paths` | Local benchmark fixture only; omit from public result rows when sensitive. |
| `check`, `allowed_changes` | Independent executable check and patch-scope rule. |

## Matched trial

One row per task, repetition, and profile (`hooks_pre` as guard-only or `context`). Keep run order, model settings, quality/check outcomes, elapsed seconds, input/output/cached tokens, hook-delivery count, hint bytes, lookup milliseconds, first hinted-path use, and discovery-action counts. Record infrastructure failure category separately. No transcript, raw prompt, file content, or raw tool command is retained.

## Gate decision

Frozen task IDs, thresholds, exclusions, analysis version, intervals, and `pass`/`fail`/`unverified` per gate. A failed or unverified gate cannot authorize a default change. Actual billed charges are optional evidence; absence means `unverified`, never zero cost.
