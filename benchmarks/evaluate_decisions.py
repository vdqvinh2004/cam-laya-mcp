#!/usr/bin/env python3
"""Compare typed Laya decisions with a small rule baseline on compact states."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from laya_agent.config import load_config  # noqa: E402
from laya_agent.policy import DecisionEngine  # noqa: E402
from laya_agent.runtime import Runtime  # noqa: E402


def simple_rule(policy: str, state: dict) -> str:
    if policy == "test_decision":
        if state.get("last_test_result") == "failed":
            return "debug_failure"
        if state.get("task_type") == "documentation":
            return "no_test_needed"
        if state.get("tests_available") is False:
            return "ask_user"
        return "full_suite" if state.get("changed_files", 0) > 10 else "targeted_test"
    if policy == "review_decision":
        if state.get("risk") == "high":
            return "request_human_review"
        if state.get("last_test_result") == "not_run":
            return "run_tests"
        return "continue" if state.get("changed_files") == 0 else "self_review"
    if state.get("last_test_result") == "failed":
        return "debug"
    if state.get("last_action") == "edit":
        return "test"
    return "review" if state.get("last_test_result") == "passed" else "inspect"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "docs/codex-decision-m5.json")
    args = parser.parse_args()
    cases = json.loads((ROOT / "benchmarks/decision_cases.json").read_text())
    config = load_config()
    runtime = Runtime(config)
    rows = []
    for case in cases:
        baseline = simple_rule(case["policy"], case["state"])
        engine = DecisionEngine(config, runtime)
        started = time.perf_counter()
        result = engine.decide(case["policy"], case["state"])
        choice = result.get("decision", result.get("risk"))
        rows.append({
            "id": case["id"], "policy": case["policy"], "expected": case["expected"],
            "simple_rule": baseline, "simple_correct": baseline == case["expected"],
            "laya_choice": choice, "laya_correct": choice == case["expected"],
            "laya_reason": result.get("reason_code"), "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        })
    report = {"model": config.model, "cases": rows, "simple_correct": sum(row["simple_correct"] for row in rows), "laya_correct": sum(row["laya_correct"] for row in rows)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"cases": len(rows), "simple_correct": report["simple_correct"], "laya_correct": report["laya_correct"]}))


if __name__ == "__main__":
    main()
