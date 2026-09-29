# CLI contract: safety-first setup

| Command | Contract |
| --- | --- |
| `cam-laya-mcp setup --guard-only` | Candidate guard-only path during evaluation. Installs detected native safety integrations without model install, checkpoint access, model daemon, or advisory MCP registration. |
| `cam-laya-mcp setup` | After the Milestone 8 gate passes, same guard-only behavior for new installs. For an existing model-enabled config, preserve preference and healthy owned model entries; report missing runtime without downloading it silently. |
| `cam-laya-mcp setup --with-model` | Guard first, then explicitly run supported-platform model setup and smoke test; add owned MCP entries only when the runtime is healthy. A model error leaves guard installed and exits nonzero. |
| `cam-laya-mcp setup --with-model --yes` | Noninteractive approval for missing model runtime installation. |
| `cam-laya-mcp setup --yes` | Compatibility alias for explicit noninteractive model setup used by old automation; document its meaning. |
| `cam-laya-mcp enable` | Enable model advice only after runtime readiness succeeds. If unavailable, leave config unchanged and explain `setup --with-model`. |
| `cam-laya-mcp disable` | Disable model advice; safety hooks remain installed. |
| `cam-laya-mcp doctor` | Read-only. Report guard configuration and observed verification separately from model preference, support, runtime/cache readiness, and MCP presence. Retain existing top-level keys where possible for existing scripts. |
| `cam-laya-mcp uninstall` | Remove only owned entries. Keep config, model runtime, and cache unless the existing explicit removal flags are passed. |

Setup must be idempotent and preserve unowned client entries and JSONC comments. Default setup must not require `uv` once this package is installed. Client hook trust, when required, is a separate user action; setup cannot report it as already complete.
