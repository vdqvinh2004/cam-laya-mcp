from __future__ import annotations

import re
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from .context import fingerprint, git_facts, project_facts
from .daemon import request
from .policy import unavailable_decision

mcp = FastMCP(
    "cam-laya-mcp",
    instructions=(
        "Use a local typed decision only when it could avoid a costly agent step. "
        "Skip routine task classification, obvious failed-test debugging, and repeated unchanged state. "
        "Use laya_test_decision for ambiguous test scope, laya_next_action for ambiguous phase changes, "
        "laya_review_decision for uncertain review needs, and laya_risk_check for ambiguous risk. "
        "Send short state facts, never secrets or source. Decisions are guidance, not permission. "
        "If unavailable or defer_to_agent, continue normally."
    ),
)
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, openWorldHint=False)

def _decide(policy: str, state: dict) -> dict:
    try:
        return request("decide", policy=policy, state=state, source="mcp", timeout=60)
    except Exception:
        return unavailable_decision(policy, state)


@mcp.tool(annotations=READ_ONLY)
def laya_status() -> dict:
    """Check local Laya-MLX availability and warm-model state when diagnosing this server."""
    try:
        return request("status", timeout=2)
    except Exception:
        return {"available": False, "runtime": "mlx", "model_loaded": False}


@mcp.tool(annotations=READ_ONLY)
def laya_decide(policy: str, state: dict) -> dict:
    """Generic decision endpoint for clients that need one tool. Prefer the named task, risk, test, action, and review tools. Returns defer_to_agent when unsure."""
    return _decide(policy, state)


@mcp.tool(annotations=READ_ONLY)
def laya_route_task(request: str, context: dict | None = None) -> dict:
    """Classify a short coding task only when its type would change tools or workflow. Skip obvious tasks and repeated unchanged state; never send source or secrets."""
    facts = {**project_facts(), **git_facts()}
    supplied = (context or {}).get("cache_revision")
    supplied = supplied if isinstance(supplied, str) and re.fullmatch(r"[0-9a-f]{64}", supplied) else ""
    revision = fingerprint(str(Path.cwd().resolve()), facts.get("cache_revision", ""), supplied)
    return _decide("route_task", {**facts, **(context or {}), "request": request, "cache_revision": revision})


@mcp.tool(annotations=READ_ONLY)
def laya_risk_check(action: str, context: dict | None = None) -> dict:
    """Before a potentially destructive command, deployment, or secret access, check risk. High/destructive requires human review; unknown means decide yourself. Never use confidence as permission."""
    return _decide("risk_check", {**(context or {}), "action": action})


@mcp.tool(annotations=READ_ONLY)
def laya_next_action(state: dict) -> dict:
    """When task phase or test result changes, choose the next workflow action. Pass short facts such as current_phase, last_test_result, and task_type."""
    return _decide("next_action", state)


@mcp.tool(annotations=READ_ONLY)
def laya_test_decision(state: dict) -> dict:
    """After code changes or a failed test, choose test scope. Pass short facts such as last_test_result, changed_files, and tests_available."""
    return _decide("test_decision", state)


@mcp.tool(annotations=READ_ONLY)
def laya_review_decision(state: dict) -> dict:
    """Before reporting completion or committing, choose a review action from short task and test facts."""
    return _decide("review_decision", state)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
