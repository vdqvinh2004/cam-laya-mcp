# Implementation plan

## Stack and boundaries

Python 3.11+ package, official `mcp` Python SDK, `laya-mlx` 0.2 API, standard library Unix sockets and JSON, and JSON5 only for OpenCode JSONC settings. Laya-MLX and MLX are installed into a separate Python 3.12 environment after explicit approval. No inference API key or PyTorch dependency.

## Architecture

`runtime.py` loads the published MLX checkpoint once; `policy.py` combines hard rules, typed choice decisions, selective digest-key caching, and mandatory-safety fallback; `context.py` compresses short project and task facts and derives a repository metadata revision. `daemon.py` shares warm model state between hook CLI calls and MCP requests, serializes decisions, and rotates local event logs. `mcp_server.py` exposes seven stdio tools. `integrations.py` owns client configuration and native hooks/plugins, including OpenCode's discovered live config source. `cli.py` handles setup, diagnostics, benchmark, and removal.

## Sequence

1. Check current upstream and official client APIs; record the capability matrix in ADR 0001.
2. Implement compact state, runtime, policy, and cache.
3. Add warm local process and MCP stdio server.
4. Add installer, CLI, client adapters, and automatic lifecycle handlers.
5. Verify hard safety, fallback, ownership, and MCP roundtrip with tests.
6. After approval, install Laya-MLX, run checkpoint smoke inference, then test detected real client configs.

## Verification

`uv run pytest -q`, `uvx ruff check --select F,I src tests`, `uv build`, `cam-laya-mcp test`, `cam-laya-mcp benchmark`, and `cam-laya-mcp doctor`. The final three require installed Laya-MLX for meaningful model results. Simulated daemon outages must fail closed when mandatory safety is enabled; end-to-end stdio tests cover stale sockets, concurrent requests, and event rotation.

See [ADR 0001](../../docs/adr/0001-local-decision-layer.md) for source-backed capability choices.
