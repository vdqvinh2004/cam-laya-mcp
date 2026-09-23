# cam-laya-mcp Constitution

## Core principles

1. **Local MLX only.** Laya-MLX is the sole decision runtime. The integration uses no PyTorch Laya fallback or cloud inference API.
2. **Coding agent owns reasoning.** Laya chooses among small typed options; the coding LLM owns repository reasoning, code generation, debugging, and explanations.
3. **Safety rules outrank model output.** Explicit destructive actions are blocked by deterministic rules. Model confidence never authorizes them.
4. **Automatic where real.** Use documented native hooks/plugins. MCP tool registration alone never claims automatic invocation.
5. **Small and private.** Send compact state, cache only safe fingerprints, log only decisions and timings, and preserve user settings.

## Quality gates

Use current upstream APIs and official client documentation. Unit tests must cover policy, cache, config, and client config ownership; an actual MCP stdio roundtrip must pass. Run local model inference after installation approval. Report benchmark measurements from the local machine only.

## Governance

The specification, plan, and ADR must remain consistent with implemented client capability. Changes to safety policy or config ownership need tests. Amend this document when product principles change.

**Version**: 1.0.0 | **Ratified**: 2026-09-23 | **Last Amended**: 2026-09-23
