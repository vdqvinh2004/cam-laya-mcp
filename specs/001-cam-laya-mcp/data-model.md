# Milestone 5 measurement records

No database or raw transcript is added. The runner stores aggregate trial data; the daemon keeps bounded local timing events.

## Decision event

`invocation_id` (random local ID), `run_id` (optional test ID), `policy`, `source` (`hook` or `mcp`), `outcome` (`hard_rule`, `cache`, `model`, `defer`, `timeout`, `failure`), `cold_model` (boolean), and nonnegative `daemon_start_ms`, `queue_ms`, `model_load_ms`, `inference_ms`, `transport_ms`, `total_ms` where observable. Missing stages are null, not zero. A safe task fingerprint may identify repeated state; raw prompt, source, commands, secrets, and model output text are excluded. Events remain bounded and rotate as existing logs do.

State: `received` → `completed` or `timed_out`/`failed`. A response timeout must not create a second decision request. Safety fallback applies before reporting a timed-out risk check.

## Codex trial

`task_id`, `repetition`, `condition`, `run_order`, `model`, `checkout_commit`, `cold_model`, `elapsed_ms`, `first_useful_response_ms`, `input_tokens`, `cached_input_tokens`, `output_tokens`, `tool_calls`, `hook_calls`, `decision_outcomes`, `check_pass`, `patch_rubric`, `errors`, and `billed_usd` (null unless observed). `cached_input_tokens` is a subset of `input_tokens`; uncached input is their difference. Optional `api_equivalent_usd` carries the dated source and rate assumptions, never a billed-cost label. No transcript, diff body, or secret is written to the aggregate result.

Trials are paired by `task_id` and `repetition` at the same commit. A trial with a missing final response, incomplete check, or tool error is a failed trial, not silently dropped.
