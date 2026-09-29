# Milestone 5 integration contract

## Existing MCP tools

The seven current tools remain read-only and accept compact state. A successful decision keeps the existing `decision` or `risk`, `confidence`, and optional `reason_code` fields. `defer_to_agent` means the agent continues its own workflow. Tool registration alone does not imply a call. The selected route owner and any smaller MCP surface must be justified by the diagnostic ablation before changing the public tool list.

## Invocation behavior

- A task boundary may produce zero or one automatic route hint. An unchanged task must not trigger another model inference or duplicate hint. Explicit MCP calls for a changed state remain available.
- A decision key includes the relevant task, repository revision, config, and model identity. Secret-bearing or arbitrary command text stays outside the cache. Different relevant context must not reuse a stale decision.
- A socket response timeout ends that invocation. Only a connection/startup failure may be retried. A risk-check timeout follows existing mandatory-safety fail-closed behavior; ordinary decisions return `defer_to_agent`.
- Hard destructive-action rules run before model output and cannot be overridden by confidence, caching, or latency gates.
- Decision metrics expose timings and outcomes without prompt text, source code, command text, or credentials. Estimated saved tokens are never presented as measured Codex savings.

The implementation may choose hook-owned routing, MCP-owned routing, or both after ablation. If both remain, they must share safe state identity; the contract above applies to either choice.
