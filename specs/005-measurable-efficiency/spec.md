# Milestone 5: Measurable Codex efficiency

**Status:** Completed; productivity gate failed.

## Goal

Determine whether selective local decisions save Codex time and tokens on real coding tasks without reducing correctness or safety.

## Acceptance and result

- Instrument per-invocation model, daemon, hook, and MCP cost without storing raw prompts or source.
- Compare disposable identical checkouts with executable checks, patch-quality review, and paired trials.
- Let simple rules and low-value paths bypass inference; keep model decisions opt-in if the benefit gate fails.

The corrected coding evaluation showed no reliable speed gain. PreToolUse+PostToolUse increased paired median token use by 17,469 tokens; billed spend was not measured. Post-test guidance remains off by default. See [efficacy evidence](../../docs/codex-efficacy-baseline.md) and [release gates](../../docs/release-readiness.md).
