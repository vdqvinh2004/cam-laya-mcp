# Milestone 6 Plan: Agent Context Retrieval

## Objective

Test one optional MCP action that can replace repository exploration: search the current repository for a task and return a short set of source and test excerpts. The action uses deterministic local search and makes no MLX or network call.

## Product decision

Keep model decisions disabled by default. Do not add prompt hooks or automatically run retrieval on every user message. Register a single `laya_find_context` tool and describe when it is worth calling: use it when a repository task does not identify its target; skip it when the task names the relevant files or asks for a simple change.

The milestone is an experiment. Register the tool only when `CAM_LAYA_CONTEXT_EXPERIMENT=1` is set by the isolated benchmark profile. Leave normal client configuration and the installed MCP surface unchanged until the tool passes the release gate.

## Design

1. Accept one bounded natural-language query; derive the repository root from the MCP process working directory. Do not accept arbitrary filesystem paths.
2. Search locally with installed platform tools or the standard library, honoring repository ignore rules where possible. Do not add a model, embeddings, index database, or package dependency.
3. Return a ranked, bounded list of source excerpts and likely test paths. Put file paths and line numbers first. Return a clear empty result when evidence is weak; do not generate summaries.
4. Constrain reads to the current repository. Skip ignored, generated, binary, oversized, secret/config, and symlinked paths. Cap query length, candidate count, and response bytes. Do not log query text or source excerpts.
5. The retrieval handler must not call the Laya daemon. Existing deterministic risk checks remain unchanged.
6. Add one concise tool description. Keep baseline, registered-but-unused MCP, and retrieval-used conditions distinguishable in the evaluation runner so prompt/schema overhead is visible. The benchmark flag must not be added to normal user settings.

## Evaluation

- Create six disposable coding tasks with hidden target paths: four repository-discovery tasks and two simple bypass tasks. Every task has an executable check and a patch rubric.
- Run a small pilot first. Confirm the agent actually calls the retrieval tool on discovery tasks, skips it on bypass tasks, and receives useful candidates. Allow one description adjustment, then stop the experiment if use remains absent or unhelpful.
- Run five counterbalanced baseline/retrieval pairs per task with identical model, reasoning effort, prompt, and disposable checkout. Run a short registered-but-unused control to estimate registration overhead.
- Record total, cached, uncached, and output tokens; first useful response; total and p95 elapsed time; executable check and patch rubric; tool turns; retrieval calls, response bytes, candidates, and handler latency; errors; billed-cost availability.
- Use the existing paired bootstrap summarizer. Label API-equivalent cost estimates separately from billed cost. Since this tool makes no model call, local model-load and inference times are not applicable.

## Release gate

Enable the tool in setup only if discovery tasks show at least 10% lower median total Codex tokens, the paired 95% token interval is below zero, quality does not regress, and median elapsed time does not increase. Claim a response-time improvement only if elapsed-time paired intervals are also below zero. Report bypass tasks and registered-but-unused overhead. If the tool is not called, returns irrelevant context, or misses the gate after the one allowed instruction adjustment, remove it and close the cost/speed retrieval experiment as unsuccessful.

## Rollout and fallback

Keep model inference off by default. If the retrieval gate passes, expose the tool through MCP while keeping it agent-invoked. If it fails, remove the new tool and retain only deterministic risk behavior; do not replace retrieval with an MLX classifier as a fallback.

## Outcome

The pilot failed the adoption gate after one guidance adjustment: Codex made zero retrieval calls on four discovery trials. The tool prototype was removed and the full paired run was skipped. See `milestone-6-research.md` and the two pilot artifacts listed there. No benefit claim is supported.

## Task order

T045–T047 define the research, acceptance criteria, and tool contract. T048–T050 implement and check the smallest local retrieval slice. T051–T052 build the hidden-target corpus and run the pilot. T053 runs the full paired evaluation. T054 records the result and applies the release gate.
