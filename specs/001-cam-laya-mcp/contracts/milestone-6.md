# Milestone 6 MCP Contract: `laya_find_context`

## Request

| Field | Type | Requirement |
| --- | --- | --- |
| `query` | string | Required, non-empty, bounded natural-language description of the code or behavior to find. |

The handler uses the repository working directory associated with the MCP server. It does not accept a caller-supplied absolute path or execute caller-provided commands.

The server exposes this tool only when `CAM_LAYA_CONTEXT_EXPERIMENT=1`; the evaluation runner sets the flag in disposable Codex configs. Normal client configs do not set it during the experiment.

## Response

Return a small JSON object with:

- `results`: ordered candidate records containing repository-relative `path`, `start_line`, `end_line`, short `excerpt`, and optional `test_paths`.
- `truncated`: whether result or byte caps removed candidates or excerpt text.
- `reason`: optional stable reason such as `no_matches`, `unsupported_repository`, or `search_error`.

No-match is a successful empty response. Errors must not return filesystem paths outside the repository or raw subprocess output.

## Limits and privacy

- Keep the query and response bounded; initial implementation should use constants rather than user-tunable knobs.
- Resolve candidates under the repository root and reject symlink escapes.
- Skip ignored/generated, binary, oversized, and secret/config paths.
- Do not persist or log the query, excerpts, or source contents.
- Do not start the Laya daemon or invoke MLX.

## Use guidance

Call only when the task leaves the relevant file or test unclear. Skip when the prompt names the target or the task is a simple bypass. Treat results as search leads; the agent must inspect the source and validate its own changes.
