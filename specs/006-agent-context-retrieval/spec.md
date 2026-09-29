# Milestone 6: Agent context retrieval

**Status:** Closed after failed adoption gate. Prototype removed.

## Goal

Test whether one bounded, deterministic MCP repository search can reduce Codex exploration on tasks whose target file is not named.

## Acceptance and outcome

The experimental `laya_find_context` tool was confined to disposable benchmark profiles, returned short repository-local candidates, and made no MLX call. The pilot required Codex to use it on discovery tasks before a larger paired run. Codex made zero retrieval calls across four discovery trials, including after one guidance adjustment. The adoption gate failed; the full paired run was skipped and the tool removed. No token or speed benefit is claimed.

See [research](research.md), [original plan](plan.md), [prototype contract](contracts/context-retrieval.md), and [pilot evidence](../../docs/codex-efficacy-baseline.md).
