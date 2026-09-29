"""Guard corpus and hook-latency runner for Milestone 8 (T002).

Evaluates benchmarks/guard_cases.json against hard_risk and measures
whole-process safe-hook latency. Reports case IDs and reason codes
only; raw commands never appear in output.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from laya_agent.policy import hard_risk  # noqa: E402


def resolve_hook_bin(explicit: str | None) -> list[str]:
    if explicit:
        return [explicit]
    found = shutil.which("cam-laya-mcp")
    if found:
        return [found]
    venv_bin = ROOT / ".venv" / "bin" / "cam-laya-mcp"
    if venv_bin.exists():
        return [str(venv_bin)]
    raise SystemExit("no cam-laya-mcp executable found; pass --hook-bin")


def evaluate_corpus(cases: list[dict]) -> dict:
    sets: dict[str, dict] = {}
    failures: list[dict] = []
    for case in cases:
        actual = hard_risk(case["action"])
        if case["expect"] == "block":
            passed = actual is not None and (case["reason"] is None or actual == case["reason"])
        else:
            passed = actual is None
        bucket = sets.setdefault(case["set"], {"total": 0, "passed": 0})
        bucket["total"] += 1
        if passed:
            bucket["passed"] += 1
        else:
            failures.append({"id": case["id"], "expected_reason": case["reason"], "actual_reason": actual})
    return {"sets": sets, "failures": failures,
            "failed": sum(s["total"] - s["passed"] for s in sets.values())}


def hook_latency(hook_bin: list[str], samples: int) -> dict:
    work = Path(tempfile.mkdtemp(prefix="guard-latency-"))
    env = dict(os.environ, HOME=str(work), XDG_CONFIG_HOME=str(work / "config"),
               XDG_STATE_HOME=str(work / "state"), CODEX_HOME=str(work / "codex"))
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git status"}})
    timings: list[float] = []
    denied = 0
    for _ in range(samples):
        start = time.perf_counter()
        proc = subprocess.run([*hook_bin, "hook", "codex", "PreToolUse"],
                              input=payload, capture_output=True, text=True, env=env, timeout=30)
        timings.append((time.perf_counter() - start) * 1000)
        try:
            response = json.loads(proc.stdout or "{}")
        except json.JSONDecodeError:
            response = None
        if proc.returncode != 0 or response is None or "deny" in str(response) or "permissionDecision" in str(response):
            denied += 1
    timings.sort()
    daemon_started = (work / "state" / "laya-agent" / "agent.sock").exists()
    p95 = timings[min(len(timings) - 1, int(len(timings) * 0.95))]
    return {"samples": samples, "median_ms": round(statistics.median(timings), 2),
            "p95_ms": round(p95, 2), "max_ms": round(timings[-1], 2),
            "denied_safe": denied, "model_daemon_started": daemon_started}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(ROOT / "benchmarks" / "guard_cases.json"))
    parser.add_argument("--latency-samples", type=int, default=20)
    parser.add_argument("--hook-bin", default=None)
    parser.add_argument("--check-gate", action="store_true",
                        help="exit nonzero if any corpus case fails")
    parser.add_argument("--p95-budget-ms", type=float, default=60.0)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    data = json.loads(Path(args.cases).read_text())
    corpus = evaluate_corpus(data["cases"])
    latency = hook_latency(resolve_hook_bin(args.hook_bin), args.latency_samples)
    summary = {"cases_file": args.cases, "case_count": len(data["cases"]),
               "corpus": corpus, "latency": latency,
               "p95_budget_ms": args.p95_budget_ms,
               "p95_within_budget": latency["p95_ms"] <= args.p95_budget_ms}
    text = json.dumps(summary, indent=1)
    if args.output:
        Path(args.output).write_text(text + "\n")
    print(text)
    if corpus["failed"] or (args.check_gate and not summary["p95_within_budget"]):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
