from typing import Any, Dict
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.logging import logger
from app.services.guardrails_service import guardrails_service


def receive_message_node(state: AgentState) -> Dict[str, Any]:
    """
    Ingress Gateway Node:
    1. Detects and blocks Prompt Injection & Jailbreak attacks (Phase 8).
    2. Redacts sensitive PII (Credit Cards, Emails, Phones, API Secrets) (Phase 8).
    3. Initializes the execution trace.
    """
    user_id = state.get("user_id", "anonymous")
    role = state.get("user_role", "customer")
    raw_message = state.get("raw_message", "").strip()

    logger.info(f"[ReceiveNode] Processing incoming message from user '{user_id}' with role '{role}' (length: {len(raw_message)} chars)")

    # 1. Prompt Injection Defense
    is_injection, injection_reason = guardrails_service.detect_prompt_injection(raw_message)

    # 2. PII Masking
    sanitized_message, pii_counts = guardrails_service.mask_pii(raw_message)

    trace = state.get("execution_trace", []) or []
    trace.append({
        "step_name": "receive_message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "security_violation" if is_injection else "success",
        "details": {
            "user_id": user_id,
            "role": str(role),
            "message_length": len(raw_message),
            "pii_redacted": pii_counts,
            "security_flag": "PROMPT_INJECTION_DETECTED" if is_injection else None
        }
    })

    if is_injection:
        return {
            "execution_trace": trace,
            "sanitized_message": sanitized_message,
            "pii_redacted": pii_counts,
            "security_flag": "PROMPT_INJECTION_DETECTED",
            "is_authorized": False,
            "authorization_error": f"Security Policy Violation: {injection_reason}",
            "error": "Prompt injection detected"
        }

    return {
        "execution_trace": trace,
        "sanitized_message": sanitized_message,
        "pii_redacted": pii_counts,
        "security_flag": None,
        "is_authorized": True,
        "error": None
    }
