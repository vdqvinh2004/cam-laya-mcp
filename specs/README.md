# Milestones

Each numbered folder owns one milestone's `spec.md`, `plan.md`, and `tasks.md`. Completed detail stays with its milestone.

| Milestone | Folder | Status |
| --- | --- | --- |
| 1 | [Local decision layer](001-cam-laya-mcp/spec.md) | Foundation and initial hardening complete. |
| 2 | [Command safety hardening](002-command-safety/spec.md) | Implemented. |
| 3 | [Client upgrade safety](003-client-upgrade-safety/spec.md) | Earlier client-config hardening complete. |
| 4 | [Codex efficacy baseline](004-codex-efficacy/spec.md) | First comparison complete; no benefit established. |
| 5 | [Measurable efficiency](005-measurable-efficiency/spec.md) | Paired evaluation complete; productivity gate failed. |
| 6 | [Agent context retrieval](006-agent-context-retrieval/spec.md) | Pilot complete; prototype removed after zero calls. |
| 7 | [Experimental release hardening](007-experimental-release/spec.md) | Completed; docs and verification only. |
| 8 | [Offline safety default](008-offline-safety-default/spec.md) | Implemented; guard-only is the default. Local Mac and Ubuntu gates passed. |
| 9 | [Measured context acceleration](009-measured-context-acceleration/spec.md) | Closed with negative result: G1 pilot failed (2/4 live discovery hits), candidate removed, guard-only unchanged. |

Release evidence and unresolved rollout gates remain in [release readiness](../docs/release-readiness.md).

Milestones 3–6 keep their original historical numbers. Milestone 2 command-safety work is implemented. Current planning is Milestone 9; in a new checkout, set `SPECIFY_FEATURE_DIRECTORY=specs/009-measured-context-acceleration`. `.specify/feature.json` is local and ignored by Git.
