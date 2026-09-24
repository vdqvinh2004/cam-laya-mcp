#!/usr/bin/env python3
"""Summarize paired Codex trials without saving transcripts."""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import statistics


def median_interval(values: list[float], draws: int = 2000) -> list[float] | None:
    if not values:
        return None
    rng = random.Random(0)
    medians = sorted(statistics.median(rng.choices(values, k=len(values))) for _ in range(draws))
    return [round(medians[int(draws * 0.025)], 3), round(medians[int(draws * 0.975)], 3)]


def api_equivalent(rows: list[dict], model: str) -> float | None:
    if model != "gpt-6-luna":
        return None
    return round(sum(((row["input_tokens"] - row["cached_input_tokens"]) * 0.10 + row["cached_input_tokens"] * 0.01 + row["output_tokens"] * 0.50) / 1_000_000 for row in rows), 8)


def summarize(rows: list[dict], baseline: str, selected: str, model: str) -> dict:
    grouped = {}
    for row in rows:
        if row["condition"] in {baseline, selected}:
            grouped.setdefault((row["task"], row["repetition"], row.get("cohort")), {})[row["condition"]] = row
    pairs = [(key, item[baseline], item[selected]) for key, item in grouped.items() if baseline in item and selected in item]
    def report(items):
        left = [a for _, a, _ in items]
        right = [b for _, _, b in items]
        token_delta = [(b["input_tokens"] + b["output_tokens"]) - (a["input_tokens"] + a["output_tokens"]) for _, a, b in items]
        time_delta = [b["elapsed_seconds"] - a["elapsed_seconds"] for _, a, b in items]
        def side(part):
            elapsed = sorted(row["elapsed_seconds"] for row in part)
            decisions = [event for row in part for event in row.get("laya_stats_delta", {}).get("decision_events", [])]
            clients = [event for row in part for event in row.get("laya_stats_delta", {}).get("client_events", [])]
            return {
                "runs": len(part), "quality_passes": sum(bool(row["quality_ok"]) for row in part),
                "total_tokens": sum(row["input_tokens"] + row["output_tokens"] for row in part),
                "uncached_input_tokens": sum(row["input_tokens"] - row["cached_input_tokens"] for row in part),
                "cached_input_tokens": sum(row["cached_input_tokens"] for row in part),
                "output_tokens": sum(row["output_tokens"] for row in part),
                "median_elapsed_seconds": round(statistics.median(elapsed), 3) if elapsed else None,
                "p95_elapsed_seconds": elapsed[min(len(elapsed) - 1, int(len(elapsed) * 0.95))] if elapsed else None,
                "median_first_response_ms": round(statistics.median(row["first_response_ms"] for row in part if row.get("first_response_ms") is not None), 2) if any(row.get("first_response_ms") is not None for row in part) else None,
                "mcp_calls": sum(sum(row["mcp_tool_calls"].values()) for row in part),
                "hook_calls": sum(row.get("laya_stats_delta", {}).get("hook_decisions", 0) for row in part),
                "decision_outcomes": {outcome: sum(event.get("outcome") == outcome for event in decisions) for outcome in sorted({event.get("outcome") for event in decisions})},
                "median_model_load_ms": round(statistics.median(event["model_load_ms"] for event in decisions if event.get("model_load_ms") is not None), 2) if any(event.get("model_load_ms") is not None for event in decisions) else None,
                "median_inference_ms": round(statistics.median(event["inference_ms"] for event in decisions if event.get("inference_ms") is not None), 2) if any(event.get("inference_ms") is not None for event in decisions) else None,
                "median_client_total_ms": round(statistics.median(event["total_ms"] for event in clients), 2) if clients else None,
                "api_equivalent_usd": api_equivalent(part, model),
            }
        return {
            baseline: side(left), selected: side(right),
            "paired_total_token_delta_median": statistics.median(token_delta) if token_delta else None,
            "paired_total_token_delta_ci95": median_interval(token_delta),
            "paired_elapsed_delta_median_seconds": round(statistics.median(time_delta), 3) if time_delta else None,
            "paired_elapsed_delta_ci95_seconds": median_interval(time_delta),
        }
    task_ids = sorted({key[0] for key, _, _ in pairs})
    return {
        "model": model, "baseline": baseline, "selected": selected, "matched_pairs": len(pairs),
        "overall": report(pairs),
        "eligible": report([item for item in pairs if item[1].get("eligible") is True]),
        "bypass": report([item for item in pairs if item[1].get("eligible") is False]),
        "cohorts": {cohort: report([item for item in pairs if item[0][2] == cohort]) for cohort in sorted({item[0][2] for item in pairs})},
        "tasks": {task: report([item for item in pairs if item[0][0] == task]) for task in task_ids},
        "api_price_source": "https://developers.openai.com/api/docs/pricing (2026-09-24, Standard short context; illustration only)" if model == "gpt-6-luna" else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("--selected", default="combined")
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    result = summarize(data["results"], "baseline", args.selected, data["model"])
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
