from __future__ import annotations

import re
import time
from collections import Counter

from .config import Config
from .context import compact, fingerprint
from .runtime import Runtime, environment

OPTIONS = {
    "route_task": ["coding", "debugging", "refactoring", "testing", "documentation", "research", "architecture", "dependency_management", "security", "devops", "configuration", "code_review"],
    "next_action": ["inspect", "search", "edit", "implement", "test", "debug", "review", "commit", "ask_user", "stop"],
    "test_decision": ["no_test_needed", "targeted_test", "unit_tests", "integration_tests", "e2e_tests", "full_suite", "debug_failure", "ask_user"],
    "review_decision": ["continue", "self_review", "run_tests", "request_human_review", "stop"],
    "risk_check": ["safe", "low", "medium", "high", "destructive"],
}
CACHE_SAFE_VALUES = frozenset({"python", "javascript", "typescript", "rust", "go", "java", "c", "cpp", "nextjs", "react", "vue", "django", "flask", "fastapi", "node", "coding", "debugging", "refactoring", "testing", "review", "repository_inspection", "implementation", "not_run", "passed", "failed", "safe", "low", "medium", "high", "destructive", "codex", "claude", "opencode", "inspect", "search", "edit", "implement", "test", "debug", "commit", "stop", "small", "large"})
SAFE_COMMANDS = frozenset({"git status", "git diff", "git log", "npm test", "pytest", "cargo test"})
HARD_RULES = (
    (r"\brm\s+(?:-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\b|\brm\s+-[rR]\s+-f\b", "destructive_command"),
    (r"\bgit\s+push\b[^\n]*(?:--force|\s-f(?:\s|$))", "force_push"),
    (r"\bterraform\s+(?:destroy|apply\b[^\n]*-auto-approve)", "infrastructure_change"),
    (r"\b(?:drop\s+(?:database|table)|truncate\s+table)\b", "database_destruction"),
    (r"\b(?:kubectl\s+delete|helm\s+uninstall)\b", "infrastructure_change"),
    (r"\b(?:sudo|su\s+-|chmod\s+777)\b", "privileged_change"),
    (r"(?:^|[/\s])(?:\.env|id_rsa|id_ed25519|credentials|secrets?\.json)(?:\s|$|[/])", "secrets_access"),
    (r"\b(?:OPENAI_API_KEY|ANTHROPIC_API_KEY|AWS_SECRET_ACCESS_KEY|GITHUB_TOKEN)\b", "credential_manipulation"),
    (r"(?i)ignore previous instructions.{0,80}(?:credentials|secrets|tokens|passwords)", "prompt_injection"),
    (r"\b(?:deploy|release)\b[^\n]*\b(?:prod|production)\b", "production_change"),
)


def hard_risk(action: str) -> str | None:
    for pattern, reason in HARD_RULES:
        if re.search(pattern, action, re.IGNORECASE):
            return reason
    return None


def should_call_laya(policy: str, state: dict, *, prior: dict | None = None) -> bool:
    if prior is not None or policy not in OPTIONS:
        return False
    if policy == "risk_check":
        return bool(state.get("action")) and hard_risk(str(state["action"])) is None
    if policy == "test_decision" and state.get("last_test_result") == "failed":
        return False
    if policy == "next_action" and state.get("current_phase") == "debugging" and state.get("last_test_result") == "failed":
        return False
    return bool(state)


class DecisionEngine:
    def __init__(self, config: Config, runtime: Runtime | None = None):
        self.config = config
        self.runtime = runtime or Runtime(config)
        self.cache: dict[str, tuple[float, dict]] = {}
        self.counts = Counter()
        self.latencies = []

    def status(self) -> dict:
        env = environment()
        return {"available": self.config.enabled and env["supported"] and env["installed"], "runtime": "mlx", "platform": env["platform"], "model_loaded": self.runtime.loaded, "version": env["version"], "latency_ms": self.latencies[-1] if self.latencies else None}

    def decide(self, policy: str, state: dict) -> dict:
        if policy not in OPTIONS:
            raise ValueError("invalid policy")
        if not isinstance(state, dict):
            raise ValueError("state must be an object")
        self.counts["requests"] += 1
        reason = hard_risk(str(state.get("action", ""))) if policy == "risk_check" else None
        if reason:
            self.counts["hard_rules"] += 1
            return {"risk": "destructive" if reason in {"destructive_command", "database_destruction", "infrastructure_change"} else "high", "requires_human": True, "confidence": 1.0, "reason_code": reason}
        if policy == "risk_check" and str(state.get("action", "")) in SAFE_COMMANDS:
            return {"risk": "safe", "requires_human": False, "confidence": 1.0, "reason_code": "deterministic_safe"}
        facts = compact(state)
        if policy == "test_decision" and facts.get("last_test_result") == "failed":
            return {"decision": "debug_failure", "confidence": 1.0, "reason_code": "failed_test"}
        if policy == "next_action" and facts.get("current_phase") == "debugging" and facts.get("last_test_result") == "failed":
            return {"decision": "debug", "confidence": 1.0, "reason_code": "failed_test"}
        if not self.config.enabled:
            if policy == "risk_check":
                return {"risk": "unknown", "requires_human": self.config.mandatory_safety, "confidence": 0.0, "reason_code": "disabled"}
            return {"decision": "defer_to_agent", "confidence": 0.0, "reason_code": "disabled"}
        if not facts and policy not in {"risk_check", "route_task"}:
            return {"decision": "defer_to_agent", "confidence": 0.0, "reason_code": "insufficient_state"}
        # Risk cache includes the action fingerprint; raw commands never enter model state or disk cache.
        # Free-form commands may contain credentials. Only cache risk checks for a small safe command set.
        safe_facts = all(not isinstance(v, str) or v in CACHE_SAFE_VALUES for v in facts.values())
        safe_action = str(state.get("action", "")) in {"git status", "git diff", "git log", "npm test", "pytest", "cargo test"}
        cacheable = safe_facts and (policy not in {"risk_check", "route_task"} or policy == "risk_check" and safe_action)
        key = fingerprint(policy, facts, str(state.get("action", "")) if policy == "risk_check" and cacheable else str(state.get("request", ""))[:160] if policy == "route_task" else "", self.config.model) if cacheable else None
        cached = self.cache.get(key) if key else None
        if cached and cached[0] > time.monotonic():
            self.counts["cache_hits"] += 1
            if state.get("would_call_llm") is True and cached[1].get("decision", cached[1].get("risk")) not in {"defer_to_agent", "unknown"}:
                self.counts["estimated_llm_calls_avoided"] += 1
                tokens = state.get("estimated_llm_tokens", 0)
                if type(tokens) is int and 0 < tokens <= 100000:
                    self.counts["estimated_tokens_saved"] += tokens
            return cached[1]
        if not should_call_laya(policy, state):
            return {"decision": "defer_to_agent", "confidence": 0.0, "reason_code": "no_useful_decision"}
        question = {"type": "choice", "instructions": f"Choose the best {policy.replace('_', ' ')} for this compact coding-agent state. Reply only by selecting one criterion.", "criteria": OPTIONS[policy]}
        model_state = dict(facts)
        if policy == "route_task":
            model_state["request"] = str(state.get("request", ""))[:320]
        elif policy == "risk_check":
            model_state["action"] = str(state.get("action", ""))[:320]
        start = time.perf_counter()
        try:
            answer = self.runtime.predict(model_state, question)
            decision = answer["choice"]
            if decision not in OPTIONS[policy]:
                raise ValueError("invalid model choice")
            confidence = float(answer["confidence"])
            result = {"decision": decision, "confidence": confidence}
            if policy == "risk_check":
                result = {"risk": decision, "requires_human": decision in {"high", "destructive"}, "confidence": confidence}
                if confidence < self.config.confidence_threshold:
                    result = {"risk": "unknown", "requires_human": self.config.mandatory_safety, "confidence": confidence, "reason_code": "low_confidence"}
            elif policy == "route_task":
                result["reason_code"] = "confidence_uncalibrated"
            elif confidence < self.config.confidence_threshold:
                result = {"decision": "defer_to_agent", "confidence": confidence, "reason_code": "low_confidence"}
            self.counts["laya_decisions"] += 1
            if state.get("would_call_llm") is True and result.get("decision", result.get("risk")) not in {"defer_to_agent", "unknown"}:
                self.counts["estimated_llm_calls_avoided"] += 1
                tokens = state.get("estimated_llm_tokens", 0)
                if type(tokens) is int and 0 < tokens <= 100000:
                    self.counts["estimated_tokens_saved"] += tokens
        except Exception:
            self.counts["laya_failures"] += 1
            result = {"decision": "defer_to_agent", "confidence": 0.0, "reason_code": "runtime_unavailable"}
            if policy == "risk_check":
                result = {"risk": "unknown", "requires_human": self.config.mandatory_safety, "confidence": 0.0, "reason_code": "runtime_unavailable"}
        latency = round((time.perf_counter() - start) * 1000, 2)
        self.latencies.append(latency)
        self.counts[policy] += 1
        if key:
            self.cache[key] = (time.monotonic() + self.config.cache_ttl_seconds, result)
        return result

    def stats(self) -> dict:
        return {"laya_decisions": self.counts["laya_decisions"], "cache_hits": self.counts["cache_hits"], "laya_failures": self.counts["laya_failures"], "hard_rules": self.counts["hard_rules"], "average_latency_ms": round(sum(self.latencies) / len(self.latencies), 2) if self.latencies else None, "estimated_llm_calls_avoided": self.counts["estimated_llm_calls_avoided"], "estimated_tokens_saved": self.counts["estimated_tokens_saved"]}
