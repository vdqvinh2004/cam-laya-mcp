from __future__ import annotations

import re

from .config import load_config
from .context import git_facts, project_facts
from .daemon import request
from .policy import hard_risk, unavailable_decision

TASK_WORD = re.compile(r"\b(implement|fix|debug|refactor|test|review|document|build|add|remove|migrate|configure|investigate)\b", re.I)
SECRET_WORD = re.compile(r"(?i)(api.?key|password|secret|credential|token)\s*[:=]")


def _call(policy: str, state: dict) -> dict:
    try:
        return request("decide", policy=policy, state=state, source="hook", timeout=5)
    except Exception:
        return unavailable_decision(policy, state)


def run(client: str, event: str, payload: dict) -> dict:
    if event == "SessionStart":
        try:
            request("preload" if load_config().preload else "status", timeout=0.5)
        except Exception:
            pass
        return {}
    if event == "UserPromptSubmit":
        prompt = str(payload.get("prompt", ""))
        if not 16 <= len(prompt) <= 320 or not TASK_WORD.search(prompt) or SECRET_WORD.search(prompt):
            return {}
        try:
            request("task_changed", timeout=1)
        except Exception:
            pass
        result = _call("route_task", {"request": prompt, **project_facts(), **git_facts()})
        decision = result.get("decision")
        if decision in {None, "defer_to_agent"}:
            return {}
        return _context(client, event, f"Local task route: {decision}.")
    if event == "PreToolUse":
        args = payload.get("tool_input") or {}
        name = str(payload.get("tool_name") or "")
        if not isinstance(args, dict):
            return {}
        if name in {"Read", "read", "read_file"}:
            path = str(args.get("filePath") or args.get("file_path") or args.get("path") or "")
            if hard_risk(path) in {"secrets_access", "credential_manipulation"}:
                return _deny(client, event, "secrets_access: obtain human approval before reading this file")
            return {}
        if name not in {"Bash", "bash", "shell", "exec_command"}:
            return {}
        command = str(args.get("command") or args.get("cmd") or "")
        if not command:
            return {}
        hint = None
        if client != "opencode" and re.search(r"\bgit\s+commit\b", command):
            facts = {**project_facts(), **git_facts()}
            test = _call("test_decision", {"current_phase": "testing", **facts})
            review = _call("review_decision", {"current_phase": "review", **facts})
            decisions = [result["decision"] for result in (test, review) if result.get("decision") not in {None, "defer_to_agent", "no_test_needed", "continue", "stop"}]
            if decisions:
                hint = "Local precommit decisions: " + ", ".join(decisions) + "."
        # Ordinary commands skip model inference. Dangerous commands use a hard rule.
        reason = hard_risk(command)
        if reason:
            return _deny(client, event, f"{reason}: obtain human approval before running this command")
        if load_config().mandatory_safety or re.search(r"\b(?:git\s+push|npm\s+publish|docker\s+push|kubectl\s+apply)\b", command):
            risk = _call("risk_check", {"action": command[:320], **git_facts()})
            if risk.get("requires_human"):
                return _deny(client, event, "Local risk check requires human approval")
        return _context(client, event, hint) if hint else {}
    if event == "PostToolUse":
        name = str(payload.get("tool_name") or "")
        if name not in {"Bash", "bash", "shell", "exec_command"}:
            return {}
        args = payload.get("tool_input") or {}
        command = str(args.get("command") or args.get("cmd") or "") if isinstance(args, dict) else ""
        if not re.search(r"\b(pytest|npm\s+test|cargo\s+test|go\s+test|vitest)\b", command):
            return {}
        response = payload.get("tool_response") or {}
        metadata = response.get("metadata") if isinstance(response, dict) else None
        exit_code = response.get("exit_code", metadata.get("exit", 0) if isinstance(metadata, dict) else 0) if isinstance(response, dict) else 0
        failed = isinstance(response, dict) and (exit_code != 0 or response.get("error"))
        if not failed:
            review = _call("review_decision", {"current_phase": "review", "last_test_result": "passed", **project_facts(), **git_facts()})
            if review.get("decision") in {"self_review", "run_tests", "request_human_review"}:
                return _context(client, event, f"Local post-test decision: {review['decision']}.")
            return {}
        result = _call("next_action", {"current_phase": "debugging", "last_test_result": "failed"})
        if result.get("decision") == "debug":
            return _context(client, event, "Local decision: debug the failed test before proceeding.")
    return {}


def _context(client: str, event: str, message: str) -> dict:
    if client == "opencode":
        return {"context": message}
    return {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}}


def _deny(client: str, event: str, reason: str) -> dict:
    if client == "opencode":
        return {"deny": True, "reason": reason}
    return {"hookSpecificOutput": {"hookEventName": event, "permissionDecision": "ask" if client == "claude" else "deny", "permissionDecisionReason": reason}}
