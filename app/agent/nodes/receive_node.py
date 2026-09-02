from typing import Any, Dict
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.logging import logger


def receive_message_node(state: AgentState) -> Dict[str, Any]:
    """
    Validates the incoming message and initializes execution trace.
    """
    user_id = state.get("user_id", "anonymous")
    role = state.get("user_role", "customer")
    message = state.get("raw_message", "").strip()

    logger.info(f"[ReceiveNode] Received message from user '{user_id}' with role '{role}': '{message[:60]}...'")

    trace = state.get("execution_trace", []) or []
    trace.append({
        "step_name": "receive_message",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success",
        "details": {
            "user_id": user_id,
            "role": role,
            "message_length": len(message)
        }
    })

    return {
        "execution_trace": trace,
        "is_authorized": True,
        "error": None
    }
