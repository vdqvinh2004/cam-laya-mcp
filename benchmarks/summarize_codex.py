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


def cluster_interval(groups: dict[str, list[float]], draws: int = 2000) -> list[float] | None:
    """Task-cluster bootstrap: resample tasks, keep all pairs of drawn tasks."""
    keys = [key for key, values in groups.items() if values]
    if not keys:
        return None
    rng = random.Random(0)
    medians = []
    for _ in range(draws):
        sample: list[float] = []
        for _ in keys:
            sample.extend(groups[rng.choice(keys)])
        medians.append(statistics.median(sample))
    medians.sort()
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
        token_pct = [100 * delta / (a["input_tokens"] + a["output_tokens"]) for (_, a, _), delta in zip(items, token_delta) if a["input_tokens"] + a["output_tokens"]]
        time_pct = [100 * delta / a["elapsed_seconds"] for (_, a, _), delta in zip(items, time_delta) if a["elapsed_seconds"]]
        time_groups: dict[str, list[float]] = {}
        token_groups: dict[str, list[float]] = {}
        for (key, a, b) in items:
            time_groups.setdefault(key[0], []).append(b["elapsed_seconds"] - a["elapsed_seconds"])
            token_groups.setdefault(key[0], []).append((b["input_tokens"] + b["output_tokens"]) - (a["input_tokens"] + a["output_tokens"]))
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
                "discovery_action_calls": sum(row.get("discovery_action_calls", 0) for row in part),
                "context_hints": sum(row.get("laya_stats_delta", {}).get("context_hints", 0) for row in part),
                "context_lookup_ms_median": round(statistics.median([row["laya_stats_delta"]["context_lookup_ms"] for row in part if row.get("laya_stats_delta", {}).get("context_lookup_ms") is not None]), 2) if any(row.get("laya_stats_delta", {}).get("context_lookup_ms") is not None for row in part) else None,
                "hinted_first_use_runs": sum(bool(row.get("hinted_first_use")) for row in part),
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
            "paired_total_token_pct_change_median": round(statistics.median(token_pct), 3) if token_pct else None,
            "paired_total_token_pct_change_ci95": median_interval(token_pct),
            "paired_elapsed_pct_change_median": round(statistics.median(time_pct), 3) if time_pct else None,
            "paired_elapsed_pct_change_ci95": median_interval(time_pct),
            "paired_total_token_delta_cluster_ci95": cluster_interval(token_groups),
            "paired_elapsed_delta_cluster_ci95_seconds": cluster_interval(time_groups),
        }
    task_ids = sorted({key[0] for key, _, _ in pairs})

    def cohort_of(row: dict) -> str:
        kind = row.get("kind")
        if kind in {"discovery", "bypass"}:
            return kind
        return "discovery" if row.get("eligible") is True else "bypass"

    return {
        "model": model, "baseline": baseline, "selected": selected, "matched_pairs": len(pairs),
        "overall": report(pairs),
        "eligible": report([item for item in pairs if cohort_of(item[1]) == "discovery"]),
        "discovery": report([item for item in pairs if cohort_of(item[1]) == "discovery"]),
        "bypass": report([item for item in pairs if cohort_of(item[1]) == "bypass"]),
        "cohorts": {cohort: report([item for item in pairs if item[0][2] == cohort]) for cohort in sorted({item[0][2] for item in pairs})},
        "tasks": {task: report([item for item in pairs if item[0][0] == task]) for task in task_ids},
        "api_price_source": "https://developers.openai.com/api/docs/pricing (2026-09-24, Standard short context; illustration only)" if model == "gpt-6-luna" else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=pathlib.Path, nargs="?")
    parser.add_argument("--selected", default="combined")
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--self-check", action="store_true")
    args = parser.parse_args()
    if args.self_check:
        rows = []
        for task, kind in (("t1", "discovery"), ("t2", "discovery"), ("t3", "bypass")):
            for repetition in (1, 2):
                rows.append({"task": task, "kind": kind, "condition": "baseline", "repetition": repetition,
                             "cohort": "mixed", "elapsed_seconds": 20.0, "first_response_ms": 1000,
                             "input_tokens": 1000, "cached_input_tokens": 800, "output_tokens": 100,
                             "mcp_tool_calls": {}, "laya_stats_delta": {}, "quality_ok": True})
                rows.append({"task": task, "kind": kind, "condition": "context", "repetition": repetition,
                             "cohort": "mixed", "elapsed_seconds": 18.0 if kind == "discovery" else 20.0,
                             "first_response_ms": 1000, "input_tokens": 900 if kind == "discovery" else 1000,
                             "cached_input_tokens": 700 if kind == "discovery" else 800,
                             "output_tokens": 100, "mcp_tool_calls": {}, "laya_stats_delta": {}, "quality_ok": True})
        result = summarize(rows, "baseline", "context", "gpt-6-sol")
        assert result["matched_pairs"] == 6
        assert result["discovery"]["baseline"]["runs"] == 4 and result["bypass"]["baseline"]["runs"] == 2
        assert result["discovery"]["paired_elapsed_pct_change_median"] == -10.0
        assert result["discovery"]["paired_total_token_pct_change_median"] == -9.091
        assert result["discovery"]["paired_elapsed_delta_cluster_ci95_seconds"] == [-2.0, -2.0]
        assert result["bypass"]["paired_elapsed_pct_change_median"] == 0.0
        print("self-check passed")
        return
    data = json.loads(args.input.read_text())
    result = summarize(data["results"], "baseline", args.selected, data["model"])
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
