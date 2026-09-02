from typing import Any, Dict
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.logging import logger
from app.schemas.intent_schema import INTENT_REQUIRED_ROLES, IntentType
from app.schemas.auth_schema import UserRole


def intent_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Evaluates Role-Based Access Control (RBAC) permissions for the classified intent.
    """
    intent = state.get("intent", IntentType.OUT_OF_SCOPE)
    user_role = state.get("user_role", UserRole.CUSTOMER)
    user_id = state.get("user_id", "unknown")
    trace = state.get("execution_trace", []) or []

    allowed_roles = INTENT_REQUIRED_ROLES.get(intent, [UserRole.ADMIN])
    is_authorized = user_role in allowed_roles

    auth_error = None
    if not is_authorized:
        allowed_roles_str = ", ".join([r.value for r in allowed_roles])
        auth_error = (
            f"Access Denied: Action '{intent.value}' requires one of the following roles: "
            f"[{allowed_roles_str}], but current role is '{user_role.value}'."
        )
        logger.warning(f"[RouterNode] Authorization failure for user '{user_id}': {auth_error}")
    else:
        logger.info(f"[RouterNode] Authorization granted for user '{user_id}' ({user_role.value}) on intent '{intent.value}'")

    trace.append({
        "step_name": "intent_routing_and_rbac",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "authorized" if is_authorized else "forbidden",
        "details": {
            "intent": intent.value if intent else None,
            "user_role": user_role.value,
            "is_authorized": is_authorized,
            "allowed_roles": [r.value for r in allowed_roles]
        }
    })

    return {
        "is_authorized": is_authorized,
        "authorization_error": auth_error,
        "execution_trace": trace
    }
