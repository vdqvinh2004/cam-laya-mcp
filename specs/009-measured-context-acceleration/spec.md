# Feature Specification: Measured Context Acceleration

**Feature Branch**: `main` (planning only; no branch created)

**Created**: 2026-09-29

**Status**: Planned; no implementation approved by this document

**Input**: Investigate and plan Milestone 9 in detail, without implementing it yet.

## User Scenarios & Testing

### User Story 1 - Relevant context arrives without an optional tool call (Priority: P1)

A Codex user asks for a coding change without naming the source file. If a supported native prompt hook runs, the agent receives a short, local list of likely files before it starts repository discovery. Clear file targets and unrelated prompts receive no hint.

**Why this priority**: Milestone 6's lookup ranked the target in the top three on four fixtures, but Codex made zero calls to the optional MCP tool. Delivery and relevance must be proven before optimizing the lookup.

**Independent Test**: In a disposable, trusted Codex profile, issue hidden-target and explicit-target prompts. Observe the native hook firing, inspect its bounded response, and verify that the named paths are tracked, inside the repository, and free of sensitive content.

**Acceptance Scenarios**:

1. **Given** a supported prompt event and a discovery task, **when** the hook runs, **then** it returns at most three relevant repository paths with one short reason each, or no hint if confidence is insufficient.
2. **Given** a prompt that names the target file, **when** the hook runs, **then** it returns no hint and performs no model inference.
3. **Given** an unsupported event, missing trust, a timeout, or a repository lookup failure, **when** the task starts, **then** ordinary coding and the existing safety guard remain available.

---

### User Story 2 - A measured task gain justifies rollout (Priority: P1)

A project maintainer can compare the candidate with today's guard-only setup on checked coding tasks. The comparison shows quality, elapsed time, total tokens, hook delivery, and actual billed cost where the provider exposes it.

**Why this priority**: Milestones 4 and 5 found no reliable productivity gain from model advice, and Milestone 8's small paired screen established nonregression only. Another prompt hook is justified only by a whole-task gain.

**Independent Test**: Run frozen, matched, counterbalanced Codex trials on hidden-target and explicit-target tasks in disposable profiles. Independent checks validate each patch; a prespecified analysis decides whether the candidate passes.

**Acceptance Scenarios**:

1. **Given** a frozen corpus and identical model settings, **when** both profiles solve each task, **then** the report pairs runs by task and repetition and includes failures rather than silently dropping them.
2. **Given** a failed quality, delivery, relevance, latency, or efficacy gate, **when** the milestone ends, **then** the candidate stays out of default setup and no efficiency claim is made.
3. **Given** all gates pass, **when** rollout is considered, **then** the measured Codex configuration is documented separately from unverified clients and billed cost is claimed only from actual billing data.

---

### User Story 3 - Existing safety and privacy remain predictable (Priority: P2)

A user who keeps the current guard-only setup receives the same safety behavior. A user who enables context can see whether its hook is installed and trusted and can disable it without changing safety protection or model preference.

**Why this priority**: A new agent hint can add latency, tokens, and privacy risk even when it appears helpful.

**Independent Test**: Repeat setup, disable, and uninstall in disposable profiles with unrelated client entries; send safe and destructive actions through the existing guard before and after context changes.

**Acceptance Scenarios**:

1. **Given** the current guard-only profile, **when** setup is rerun, **then** no new prompt event, MCP server, model download, or daemon starts unless the user explicitly opts into the experiment or a later gate authorizes rollout.
2. **Given** context is enabled, **when** it is disabled or uninstalled, **then** only owned context entries are removed and the safety guard remains active.
3. **Given** a prompt containing a credential or a sensitive path, **when** the hook runs, **then** neither its output nor diagnostic records reveal that value.

### Edge Cases

- Native prompt events or additional-context responses differ from documented behavior, or trust prevents the hook from running.
- The repository is large, absent, dirty, or contains symlinks, generated files, vendored code, secret paths, or ambiguous matches.
- A task names a path that does not exist, or the likely target is untracked.
- A prompt contains private text; the lookup must not persist it or send it to an external service.
- A trial fails because of client authentication, network service, rate limits, or model drift; infrastructure exclusions must follow a frozen rule and be reported.
- OpenCode has no documented prompt event in the current integration; its support must not be inferred from Codex results.

## Requirements

### Functional Requirements

- **FR-001**: Before building the candidate, verify the current native prompt-hook input and response contract against official client documentation and an isolated live Codex trial. Stop the candidate if reliable delivery is unavailable.
- **FR-002**: The candidate MUST be opt-in during evaluation and MUST leave default guard-only setup, destructive-action decisions, existing model preferences, and owned/unowned client configuration intact.
- **FR-003**: A qualifying prompt MAY receive at most three repository-local tracked paths and short reasons. An explicit-target or low-confidence prompt MUST receive no hint. No raw source excerpt is required.
- **FR-004**: Lookup MUST stay local, exclude sensitive and generated paths, reject paths outside the repository, avoid persistent raw prompt or source logs, and never invoke Laya-MLX or a cloud retrieval service.
- **FR-005**: The hook MUST fail open for context on timeout or lookup error without weakening the existing pre-tool safety guard. It MUST not require MCP tool adoption.
- **FR-006**: Evaluation MUST separate six pilot tasks from a frozen, untouched main set of at least 12 coding tasks from at least two pinned repositories. The main set has eight hidden-target discovery tasks and four explicit-target or simple bypass tasks. Each task needs an independent executable check and a patch-scope review rule.
- **FR-007**: The main study MUST use at least four matched, counterbalanced pairs per task with the same Codex model and reasoning settings. It MUST record quality, time, input/output tokens, delivered hints, discovery actions, and infrastructure failures.
- **FR-008**: The report MUST separate measured token use, published-price estimates, and actual billed charges. It MUST make no billed-cost saving claim without attributable billing records.
- **FR-009**: Any expansion to Claude Code or OpenCode MUST have its own documented event contract and live delivery trial; unverified clients MUST be labeled unverified.
- **FR-010**: If any release gate fails, the context candidate and prompt-hook registration MUST be removed. Keep the benchmark evidence and default guard behavior; prior safety coverage MUST remain unchanged.

### Key Entities

- **Context hint**: Ephemeral qualifying decision, up to three safe path/reason pairs, delivery status, and lookup time; never raw prompt or file contents in records.
- **Coding task**: Pinned repository state, task prompt, hidden target class, allowed patch scope, and independent check.
- **Matched trial**: Task, repetition, profile, run order, quality result, elapsed time, tokens, discovery actions, and hook observations.
- **Gate decision**: Frozen thresholds, eligible population, exclusions, measured results, and rollout outcome.

## Success Criteria

### Measurable Outcomes

- **SC-001 (delivery)**: An isolated live Codex trial observes the prompt hook and its additional context on every qualifying pilot run; no untrusted or unverified client is counted as supported.
- **SC-002 (relevance and bypass)**: On the eight frozen hidden-target tasks, the correct target appears in the top three on at least seven; all four bypass tasks receive no hint. Zero sensitive or out-of-repository paths are emitted.
- **SC-003 (latency)**: On the reference Mac, local context lookup has p95 at most 250 ms across 100 qualifying prompts; timeout and error paths leave the agent usable. The existing guard corpus and hook latency gates still pass.
- **SC-004 (quality)**: Candidate task-check pass count is no lower than guard-only across the 48 matched pairs, and both profiles pass at least 95% of independent checks. No new safety denial is bypassed, and all patch-scope violations are reported.
- **SC-005 (efficacy)**: In the prespecified hidden-target cohort, median paired elapsed time and total input-plus-output tokens each decrease by at least 10% versus guard-only, with each paired 95% bootstrap interval wholly below zero. The bypass cohort has no more than 5% median increase in either measure. Otherwise, no productivity claim or default rollout.
- **SC-006 (cost and transparency)**: Report complete task-level measurements, excluded infrastructure runs, and a reproducible gate decision. Claim billed savings only if per-run billed charges are available and decrease under the same paired analysis.

## Assumptions

- Milestone 8 remains the stable guard-only baseline; its hosted CI and release checks should finish before a Milestone 9 rollout decision.
- Codex is the first evaluation client. Official Codex documentation supports `UserPromptSubmit` context, but the installed client's live delivery still requires verification. Current guard-only setup does not register this event.
- A bounded local path hint is the smallest new automatic assistance worth testing after optional MCP retrieval saw zero calls. It is a hypothesis, not a promised speed gain.
- Model advice stays opt-in, and no project rewrite, new dependency, index, or extra client support is justified before the efficacy gate passes.
