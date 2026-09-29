# Feature Specification: Offline Safety Default

**Feature Branch**: `008-offline-safety-default`  
**Created**: 2026-09-28  
**Status**: Implemented; local release gates passed  
**Input**: Plan a major improvement to the project; a full rebuild is allowed if evidence supports it.

## User Scenarios & Testing

### User Story 1 - Useful setup without a model (Priority: P1)

A coding-agent user installs the package and runs setup on a supported Mac or Linux host. The agent gains local command and sensitive-file protection without downloading a checkpoint, starting a model process, or requiring Apple Silicon.

**Why this priority**: Current setup requires Apple Silicon and a successful model smoke test even though model decisions are disabled by default. This blocks the feature that already works without MLX.

**Independent Test**: In a clean supported profile with no Laya-MLX, run setup, then send safe and destructive tool actions through an installed client hook. Safe work proceeds and destructive work receives the client's documented review or deny result.

**Acceptance Scenarios**:

1. **Given** an installed CLI on macOS or Linux with no model files, **when** the user runs default setup, **then** detected client safety hooks install without a model download or model smoke test.
2. **Given** a safety-only installation, **when** a client proposes a covered destructive command or sensitive-file read, **then** the native integration returns a stable reason and requires review or denies the action according to client capability.
3. **Given** a routine safe command, **when** a client calls the hook, **then** it completes without starting the model service or adding an agent hint.

---

### User Story 2 - Explicit model experiment and safe upgrade (Priority: P1)

An existing user keeps their chosen model setting and unrelated client configuration through an upgrade. A new user opts into MLX separately when the platform supports it; declining or failing model installation leaves the safety integration usable.

**Why this priority**: A new default must not silently disable an existing experiment or take ownership of another tool's settings.

**Independent Test**: Run setup twice against clean and existing temporary client profiles, including an existing model-enabled config and unowned entries. Verify owned entries update once, model state is preserved, and a failed optional model install leaves the guard working.

**Acceptance Scenarios**:

1. **Given** a new safety-only installation, **when** the user explicitly requests model setup on supported Apple Silicon, **then** the existing local Laya-MLX path becomes available without changing the safety decisions.
2. **Given** an existing model-enabled installation, **when** the user upgrades or reruns setup, **then** their model choice and owned integration remain available; unrelated client entries remain untouched.
3. **Given** an unsupported model host or failed checkpoint setup, **when** optional model setup ends, **then** the user receives a clear model error and the safety integration still works.

---

### User Story 3 - Clear status and low overhead (Priority: P2)

A user can tell whether safety hooks are installed, which client still needs trust or manual configuration, and whether the optional model is usable. Routine coding receives no repeated model advice or unnecessary process startup.

**Why this priority**: Prior evaluations found no proven speed or cost benefit from advice and showed extra token use in one hook profile.

**Independent Test**: Run diagnostics and a paired client workload before and after the redesign. Inspect integration state, hook latency, agent time and tokens, and whether any optional model calls occurred.

**Acceptance Scenarios**:

1. **Given** a guard-only setup, **when** the user runs diagnostics, **then** guard installation and model availability appear as separate states.
2. **Given** a client whose hooks require a trust review, **when** diagnostics run before trust, **then** the result does not claim live hook execution.
3. **Given** routine coding tasks, **when** the guard profile runs, **then** no model advice or MCP tool surface is added by default.

### Edge Cases

- A client is absent, partially configured, or has an unowned entry with the same name.
- Existing config enables the model but its runtime or checkpoint is missing.
- A shell command is malformed, nested, quoted, or assembled dynamically. The guard must describe its coverage honestly and must not claim to be a sandbox.
- A client cannot request approval from a hook. The response must match its documented deny/manual-action behavior.
- Setup or uninstall is interrupted after one client is updated; a retry must be safe.
- A user supplies a sensitive path in quotes or a command containing secret text; diagnostics and event records must not retain raw text.

## Requirements

### Functional Requirements

- **FR-001**: Default setup MUST install usable local safety integrations on supported macOS and Linux hosts without requiring Laya-MLX, Apple Silicon, a checkpoint, or a model smoke test.
- **FR-002**: Default safety checks MUST run locally before any optional model or daemon path and MUST not start those paths for routine actions.
- **FR-003**: Covered destructive commands and sensitive-file reads MUST produce a stable reason and the client's supported review or deny response. Model confidence MUST NOT override them.
- **FR-004**: Optional model installation and enablement MUST require an explicit user action; model failure MUST NOT disable an already installed safety integration.
- **FR-005**: Existing model-enabled settings MUST survive upgrade. New installs MUST start with model advice and post-test guidance disabled.
- **FR-006**: Setup, repair, and uninstall MUST change only entries owned by this project and MUST preserve unrelated settings and comments.
- **FR-007**: A new guard-only setup MUST omit unused model-advice MCP registration and extra hook events. Users who explicitly enable the model MUST retain access to the existing typed decision tools.
- **FR-008**: Diagnostics MUST report safety integration, client trust or connection limits, and optional model readiness separately. Configuration alone MUST NOT be reported as proof of live client execution.
- **FR-009**: Event records MUST NOT retain raw prompts, commands, file contents, credentials, or sensitive paths.
- **FR-010**: Uninstall MUST remove owned safety and optional model entries without deleting shared model caches or unrelated client data by default.
- **FR-011**: Release claims MUST be backed by a labeled command corpus, client-boundary checks, and paired task measurements; absent client binaries or trust review MUST be called out as unverified.

### Key Entities

- **Installation state**: Which clients have owned safety hooks, which have optional model access, and what remains unverified.
- **Safety outcome**: Whether a tool action proceeds, requires review, or is denied, with a stable reason and no retained raw action.
- **Model state**: Opt-in preference and observed runtime readiness; model availability never substitutes for safety outcome.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Default setup succeeds from an installed CLI in clean macOS and Linux test profiles with no Laya-MLX or checkpoint present; it performs zero model downloads and starts zero model processes.
- **SC-002**: Every covered destructive case in the locked and independently reviewed holdout sets is stopped; at least 99 of 100 independently labeled benign actions proceed. Report locked and holdout results separately.
- **SC-003**: Guard-only hook overhead is at most 60 ms at p95 across 100 routine actions on the reference Mac, down from the measured 105 ms p95 baseline, with zero model-service starts. Report Linux measurements separately.
- **SC-004**: Repeated setup, upgrade, and uninstall preserve all unowned entries across Codex, Claude Code, and OpenCode fixtures. At least one client has an observed live safe-pass and dangerous-block trial; other clients are called verified only after the same observation.
- **SC-005**: Across at least six benign coding tasks with three matched pairs each, task-check pass rate does not fall and median elapsed time and tokens each rise by less than 5% against no integration. Any speed or cost claim still needs the existing separate efficacy gate.
- **SC-006**: A new user can understand from one diagnostic result whether safety is installed, whether a client needs trust or manual action, and whether optional MLX is ready.

## Assumptions

- The package and Python 3.11+ are already installed; “offline setup” means no model download or network call after package installation.
- macOS and Linux are first-class guard targets. Windows support waits for native-client and path testing.
- Existing Laya-MLX remains the only model decision runtime, available only on its supported Apple Silicon environment.
- The coding agent continues to own repository reasoning, code generation, and review. This milestone improves default protection and setup, not model advice accuracy.
- A static guard covers defined risk families. It does not execute commands, inspect external scripts, or promise complete shell isolation.
