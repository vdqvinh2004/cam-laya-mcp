# Milestone 6 Research: Agent Context Retrieval

## Decision

Run one bounded experiment: add an optional, deterministic MCP tool that finds a small amount of relevant source and test context from a natural-language task. Do not use Laya-MLX for retrieval or ranking in this milestone.

## Evidence

- Milestone 5 evaluated 30 paired coding runs per profile. Combined used 2,536,378 tokens versus 2,543,136 baseline, while median elapsed time rose from 29.63 s to 36.33 s. The paired token interval included zero; paired elapsed time was +4.515 s [95% CI +3.425, +7.805].
- The combined coding profile made zero MCP calls and recorded zero hook decisions. The six fixtures named the file to edit, so the benchmark did not test repository discovery.
- On the 12-case decision corpus, simple deterministic rules scored 12/12 and Laya scored 4/12. A cold Laya decision loaded for 36.88 s; the warm local inference took 0.20 s but returned `defer_to_agent` in the tagged review example.
- The application currently exposes seven typed decision tools. `project_facts` and `git_facts` provide project metadata and change state, but not source excerpts or a relevant-test map. MCP descriptions guide agents to call only when useful; tool registration alone does not cause calls.
- Model decisions now default off. Existing deterministic risk checks remain available.

## Options considered

| Option | Decision | Reason |
| --- | --- | --- |
| Improve the local classifier with more prompt tuning | Reject for this milestone | It did not beat simple rules and was not used during coding tasks. |
| Have MLX summarize source or generate code | Reject | Adds model latency and quality risk before there is evidence that the agent needs generated content. |
| Deterministic context retrieval | Test | One useful lookup could replace several agent searches and file reads; this has not yet been measured. |
| Stop active development | Chosen after the pilot | The model-advice thesis failed its efficacy gate, and optional retrieval was not adopted by Codex. Keep deterministic local safety available; resume agent-performance work only when a client integration can reliably perform a useful action and a paired benchmark shows net benefit. |

## Constraints and risks

- MCP registration and instructions consume prompt context, and the tool response also becomes model input. Retrieval must return less context than it saves.
- Codex can already use shell search tools efficiently. The benchmark must show agent work saved, not just that the MCP tool returns plausible matches.
- Tasks that state the exact target path cannot measure retrieval value. The new fixtures must hide target paths and include both discovery-worthy and simple bypass tasks.
- Search results may expose sensitive source. Search only within the selected repository, cap result count and excerpt bytes, exclude secret/config and generated paths, and never send results to a remote service.
- Avoid embeddings, a persistent index, a model call, a new dependency, and automatic prompt hooks in the first slice. Add any of those only if the simple experiment identifies a specific failure.

## Research conclusion

Milestone 6 should test whether an agent-facing retrieval action saves enough exploration to offset the MCP schema and returned context. It is an experiment with a stop gate, not a commitment to a large rewrite.

## Pilot outcome

The deterministic helper ranked an expected source file in the top three for all four discovery fixtures; all six fixture checks failed before a fix. That established search relevance on the fixtures only.

Codex then ran the three-case pilot twice: first with the initial MCP description, then with a stronger instruction to call retrieval before shell search. Across both pilots it made **zero retrieval calls on all four discovery trials** and zero on the explicit-target bypass trials. It used shell commands instead. The first candidate run failed one fixture check; the adjusted-guidance run passed all three. Pilot artifacts are `docs/codex-context-m6-pilot.json` and `docs/codex-context-m6-pilot-guidance.json`.

The adoption gate failed after the one permitted guidance adjustment. The full repeated benchmark was stopped. No token or latency benefit is claimed from these small pilots; they show that optional MCP registration and server guidance did not cause Codex to use the tool. The prototype was removed.

## Project status

Active development is paused. The Milestone 5 paired coding benchmark showed no demonstrated token benefit and higher median response time with Laya enabled; agents made zero MCP calls and hook decisions in coding runs. The Milestone 6 pilot showed zero retrieval calls across four discovery trials. These results do not prove the approach can never help, but they do not justify further performance work on the current advice pattern. Keep model inference off by default and retain deterministic risk checks. Reopen the performance effort only when a client integration can reliably perform a useful action and a paired benchmark demonstrates net benefit.
