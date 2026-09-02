from typing import Literal
from app.agent.state import AgentState
from app.schemas.intent_schema import IntentType
from app.core.logging import logger


ResponseNodeName = Literal[
    "handle_greeting",
    "handle_knowledge_search",
    "handle_my_tickets_search",
    "handle_ticket_create_update",
    "handle_external_api_search",
    "handle_sensitive_operation",
    "handle_database_query",
    "handle_unauthorized",
    "handle_fallback"
]


def route_after_rbac_check(state: AgentState) -> ResponseNodeName:
    """
    Conditional routing function:
    1. If authorization failed -> route to 'handle_unauthorized'.
    2. If authorized -> route to the specialized node for the detected intent.
    """
    is_authorized = state.get("is_authorized", False)
    intent = state.get("intent", IntentType.OUT_OF_SCOPE)

    if not is_authorized:
        logger.info("[RoutingRules] Routing to 'handle_unauthorized' due to RBAC restriction.")
        return "handle_unauthorized"

    routing_map = {
        IntentType.GREETING: "handle_greeting",
        IntentType.KNOWLEDGE_SEARCH: "handle_knowledge_search",
        IntentType.MY_TICKETS_SEARCH: "handle_my_tickets_search",
        IntentType.TICKET_CREATE_UPDATE: "handle_ticket_create_update",
        IntentType.EXTERNAL_API_SEARCH: "handle_external_api_search",
        IntentType.SENSITIVE_OPERATION: "handle_sensitive_operation",
        IntentType.DATABASE_QUERY_OPERATION: "handle_database_query",
        IntentType.OUT_OF_SCOPE: "handle_fallback",
    }

    target_node = routing_map.get(intent, "handle_fallback")
    logger.info(f"[RoutingRules] Routing intent '{intent.value if intent else 'None'}' to node '{target_node}'")
    return target_node
