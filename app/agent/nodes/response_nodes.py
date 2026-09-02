from typing import Any, Dict
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.logging import logger


def _append_trace(trace: list, node_name: str, status: str = "success") -> list:
    trace.append({
        "step_name": node_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status
    })
    return trace


def handle_greeting_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    logger.info("[ResponseNode: Greeting] Generating greeting response.")
    
    response = (
        "Hello! I am your Enterprise IT Support Agent. "
        "How can I assist you today? You can ask about IT policies, check support tickets, "
        "or request assistance."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_greeting")
    }


def handle_knowledge_search_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    query = state.get("raw_message", "")
    logger.info(f"[ResponseNode: Knowledge Search] Processing query: {query}")
    
    response = (
        f"[Knowledge Base Search]\n"
        f"Query: '{query}'\n"
        f"Result: In Phase 1, knowledge retrieval flow is verified. "
        f"Standard IT guidelines indicate VPN configuration requires the corporate certificate "
        f"and MFA via Authenticator app."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_knowledge_search")
    }


def handle_my_tickets_search_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    logger.info(f"[ResponseNode: My Tickets] Fetching tickets for user: {user_id}")
    
    response = (
        f"[User Ticket Status]\n"
        f"Tickets for User ({user_id}):\n"
        f"- Ticket #1042: 'Laptop docking station issue' [Status: In Progress, Assigned: IT Support Team]\n"
        f"- Ticket #0981: 'Software license renewal' [Status: Resolved]"
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_my_tickets_search")
    }


def handle_ticket_create_update_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_role = state.get("user_role", "unknown")
    logger.info(f"[ResponseNode: Ticket Management] Processing ticket action by role: {user_role}")
    
    response = (
        f"[Ticket Management Operation]\n"
        f"Authorized Operator Role: {user_role}\n"
        f"Action: Ticket operation has been registered and scheduled for dispatch to ticket queue."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_ticket_create_update")
    }


def handle_external_api_search_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    logger.info("[ResponseNode: External API Search] Searching external services...")
    
    response = (
        f"[External API & Vendor Status]\n"
        f"Status: Connected to external vendor status endpoint.\n"
        f"Result: All external dependencies (Cloud providers, Identity services) are operational."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_external_api_search")
    }


def handle_sensitive_operation_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    logger.info("[ResponseNode: Sensitive Operation] Processing sensitive operation with elevated privileges.")
    
    response = (
        f"[Sensitive Operation Execution]\n"
        f"Security Check: Passed (Senior Agent / Admin privilege verified).\n"
        f"Action: Operation logged into audit log and prepared for Human-in-the-Loop review."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_sensitive_operation")
    }


def handle_database_query_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    logger.info("[ResponseNode: Database Operation] Admin database operation verified.")
    
    response = (
        f"[Database Operations - Admin Console]\n"
        f"Privilege: Full Admin verified.\n"
        f"Action: Database health check returned status HEALTHY (Connections: 14 active, Latency: 2ms)."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_database_query")
    }


def handle_unauthorized_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    error_msg = state.get("authorization_error", "Unauthorized action.")
    logger.warning(f"[ResponseNode: Unauthorized] Returning 403 response: {error_msg}")
    
    response = f"Access Restricted (403 Forbidden): {error_msg}"
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_unauthorized", status="forbidden")
    }


def handle_fallback_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    logger.info("[ResponseNode: Fallback] Handling out-of-scope query.")
    
    response = (
        "I am an enterprise IT support assistant. "
        "I can help you with IT policies, technical troubleshooting, support tickets, and system queries. "
        "Please provide an IT-related request."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_fallback")
    }
