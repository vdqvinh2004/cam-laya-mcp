# Milestone 8 state model

No database or raw command store is added. Existing config and integration ownership files remain in place.

## User preferences

`enabled` continues to mean **model advice enabled**, not “safety enabled.” `post_test_guidance`, `mandatory_safety`, model ID, and thresholds keep their current meaning. New config defaults leave model advice and post-test guidance off. A guard-only installation is determined by owned client hook entries, so no duplicate `guard_enabled` flag is needed.

Migration: an existing `enabled = true` remains true. If its runtime is missing, diagnostics report “requested but unavailable”; setup does not silently turn it off or authorize a model download without explicit approval.

## Owned integration

The current manifest remains the source of ownership for each client's hook, plugin, and MCP entry. An adapter can install either guard-only entries or guard-plus-model entries. Unknown, edited, or repointed entries are unowned and must not be overwritten or deleted. Repeated setup converges on one owned entry per configured event.

State transitions:

```text
uninstalled -> guard_only -> guard_plus_model
      ^            ^                 |
      |            +-- model failure-+
      +--------- uninstall ----------+
```

An interrupted transition can be retried. A failed optional model install preserves `guard_only` and existing user preferences.

## Safety outcome

One in-memory result per recognized pre-tool action: `allow`, `review`, or `deny`, plus a stable reason code for non-allow results. Client adapters map `review` to their supported approval or deny behavior. Raw commands and paths exist only in process memory while evaluating the action; persistent events may keep reason, client, time, and outcome, never the raw action.

## Diagnostic snapshot

Separate facts for guard configuration, observed live hook execution, client trust/connection uncertainty, model preference, model runtime support, checkpoint readiness, and MCP registration. A configured hook without a witnessed event has status `configured`, not `verified`.
