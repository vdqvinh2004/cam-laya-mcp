from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .daemon import request
from .policy import unavailable_decision

mcp = FastMCP(
    "cam-laya-mcp",
    instructions=(
        "Use this local decision aid at task boundaries: call laya_route_task when a coding request starts; "
        "laya_test_decision after code changes or test failures; laya_next_action when phase or test result changes; "
        "laya_review_decision before declaring work ready; laya_risk_check before potentially destructive actions. "
        "Send short state facts, never secrets or source. Decisions are guidance, not permission. "
        "Avoid repeated calls for unchanged state; if unavailable or defer_to_agent, continue normally."
    ),
)

def _decide(policy: str, state: dict) -> dict:
    try:
        return request("decide", policy=policy, state=state, source="mcp", timeout=60)
    except Exception:
        return unavailable_decision(policy, state)


@mcp.tool()
def laya_status() -> dict:
    """Check local Laya-MLX availability and warm-model state when diagnosing this server."""
    try:
        return request("status", timeout=2)
    except Exception:
        return {"available": False, "runtime": "mlx", "model_loaded": False}


@mcp.tool()
def laya_decide(policy: str, state: dict) -> dict:
    """Generic decision endpoint for clients that need one tool. Prefer the named task, risk, test, action, and review tools. Returns defer_to_agent when unsure."""
    return _decide(policy, state)


@mcp.tool()
def laya_route_task(request: str, context: dict | None = None) -> dict:
    """At the start of a coding task, classify the short user request once. Context may include language, framework, or changed_files; never send source or secrets."""
    return _decide("route_task", {**(context or {}), "request": request})


@mcp.tool()
def laya_risk_check(action: str, context: dict | None = None) -> dict:
    """Before a potentially destructive command, deployment, or secret access, check risk. High/destructive requires human review; unknown means decide yourself. Never use confidence as permission."""
    return _decide("risk_check", {**(context or {}), "action": action})


@mcp.tool()
def laya_next_action(state: dict) -> dict:
    """When task phase or test result changes, choose the next workflow action. Pass short facts such as current_phase, last_test_result, and task_type."""
    return _decide("next_action", state)


@mcp.tool()
def laya_test_decision(state: dict) -> dict:
    """After code changes or a failed test, choose test scope. Pass short facts such as last_test_result, changed_files, and tests_available."""
    return _decide("test_decision", state)


@mcp.tool()
def laya_review_decision(state: dict) -> dict:
    """Before reporting completion or committing, choose a review action from short task and test facts."""
    return _decide("review_decision", state)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
