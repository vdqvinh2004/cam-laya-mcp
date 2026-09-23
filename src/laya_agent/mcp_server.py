from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .daemon import request
from .policy import hard_risk

mcp = FastMCP("cam-laya-mcp")

def _decide(policy: str, state: dict) -> dict:
    try:
        return request("decide", policy=policy, state=state, timeout=60)
    except Exception:
        if policy == "risk_check":
            reason = hard_risk(str(state.get("action", "")))
            return {"risk": "high" if reason else "unknown", "requires_human": bool(reason), "confidence": 0.0, "reason_code": reason or "runtime_unavailable"}
        return {"decision": "defer_to_agent", "confidence": 0.0, "reason_code": "runtime_unavailable"}


@mcp.tool()
def laya_status() -> dict:
    """Check local Laya-MLX availability and warm-model state."""
    try:
        return request("status", timeout=2)
    except Exception:
        return {"available": False, "runtime": "mlx", "model_loaded": False}


@mcp.tool()
def laya_decide(policy: str, state: dict) -> dict:
    """Get one compact typed decision from a compact coding state."""
    return _decide(policy, state)


@mcp.tool()
def laya_route_task(request: str, context: dict | None = None) -> dict:
    """Classify a short user task into a coding workflow category."""
    return _decide("route_task", {**(context or {}), "request": request})


@mcp.tool()
def laya_risk_check(action: str, context: dict | None = None) -> dict:
    """Assess tool action risk; deterministic dangerous-action rules take precedence."""
    return _decide("risk_check", {**(context or {}), "action": action})


@mcp.tool()
def laya_next_action(state: dict) -> dict:
    """Select the next small workflow action."""
    return _decide("next_action", state)


@mcp.tool()
def laya_test_decision(state: dict) -> dict:
    """Select a suitable test scope from compact repository state."""
    return _decide("test_decision", state)


@mcp.tool()
def laya_review_decision(state: dict) -> dict:
    """Select a review or readiness action."""
    return _decide("review_decision", state)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
