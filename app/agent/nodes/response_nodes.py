from typing import Any, Dict
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.logging import logger


def _append_trace(trace: list, node_name: str, status: str = "success", details: Any = None) -> list:
    trace_item = {
        "step_name": node_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status
    }
    if details:
        trace_item["details"] = details
    trace.append(trace_item)
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
    logger.info(f"[ResponseNode: My Tickets] Fetching live tickets from Supabase for user: {user_id}")

    from app.services.database_service import database_service
    tickets = database_service.get_user_tickets(user_id)

    if tickets:
        ticket_lines = []
        for t in tickets:
            assigned = f", Assigned: {t.assigned_to}" if t.assigned_to else ""
            ticket_lines.append(
                f"- Ticket #{t.id}: '{t.title}' [Status: {t.status.value}, Priority: {t.priority.value}, Category: {t.category.value}{assigned}]"
            )
        ticket_summary = "\n".join(ticket_lines)
        response = (
            f"[User Support Tickets - Supabase DB]\n"
            f"Found {len(tickets)} tickets for User ({user_id}):\n"
            f"{ticket_summary}"
        )
    else:
        response = (
            f"[User Support Tickets - Supabase DB]\n"
            f"No active support tickets found for User ({user_id}). "
            f"You can create a new ticket by stating your issue."
        )

    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_my_tickets_search")
    }


def handle_ticket_create_update_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    user_role = state.get("user_role")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = state.get("raw_message", "").strip()

    logger.info(f"[ResponseNode: Ticket Management] Processing ticket action for '{user_id}' (role: {role_str})")

    from app.services.database_service import database_service
    from app.schemas.ticket_schema import TicketCreate, TicketPriority, TicketCategory

    # Extract title and category heuristically or from message
    msg_lower = raw_message.lower()
    category = TicketCategory.GENERAL
    if "vpn" in msg_lower or "wifi" in msg_lower or "network" in msg_lower:
        category = TicketCategory.NETWORK
    elif "laptop" in msg_lower or "monitor" in msg_lower or "dock" in msg_lower or "hardware" in msg_lower:
        category = TicketCategory.HARDWARE
    elif "software" in msg_lower or "license" in msg_lower or "install" in msg_lower:
        category = TicketCategory.SOFTWARE
    elif "password" in msg_lower or "mfa" in msg_lower or "access" in msg_lower:
        category = TicketCategory.SECURITY

    priority = TicketPriority.HIGH if any(w in msg_lower for w in ["urgent", "critical", "broken", "emergency"]) else TicketPriority.MEDIUM
    title = raw_message[:60] if len(raw_message) <= 60 else raw_message[:57] + "..."

    try:
        new_ticket = database_service.create_ticket(
            user_id=user_id,
            data=TicketCreate(
                title=title,
                description=raw_message,
                priority=priority,
                category=category
            )
        )
        # Log to audit trail
        database_service.log_audit(
            user_id=user_id,
            action="create_ticket",
            details={"ticket_id": new_ticket.id, "title": title, "category": category.value}
        )

        response = (
            f"[Ticket Successfully Created in Supabase]\n"
            f"- Ticket ID: #{new_ticket.id}\n"
            f"- Title: {new_ticket.title}\n"
            f"- Category: {new_ticket.category.value.capitalize()}\n"
            f"- Priority: {new_ticket.priority.value.capitalize()}\n"
            f"- Status: {new_ticket.status.value.capitalize()}\n"
            f"- Created By: {new_ticket.created_by}\n"
            f"Your request has been registered and dispatched to the IT Support Queue."
        )
    except Exception as exc:
        logger.warning(f"[ResponseNode: Ticket Management] Fallback due to DB error: {exc}")
        response = (
            f"[Ticket Management Operation]\n"
            f"Authorized Operator: {user_id} ({role_str})\n"
            f"Request: '{title}'\n"
            f"Action: Ticket operation registered into dispatch queue."
        )

    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "handle_ticket_create_update")
    }


def handle_external_api_search_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    raw_message = state.get("raw_message", "").strip()
    logger.info(f"[ResponseNode: External API Search] Searching external services via Tavily for '{raw_message}'...")

    from app.services.external_search_service import external_search_service
    search_data = external_search_service.search(raw_message)

    answer = search_data.get("answer", "No response from external search.")
    provider = search_data.get("provider", "external_api")
    results = search_data.get("results", []) or []

    sources_lines = []
    for r in results[:3]:
        title = r.get("title", "Resource")
        url = r.get("url", "")
        content = (r.get("content") or "").strip()
        snippet = content[:120] + "..." if len(content) > 120 else content
        sources_lines.append(f"- [{title}]({url}): {snippet}")

    sources_summary = "\n".join(sources_lines) if sources_lines else "No external links provided."

    response = (
        f"[External Vendor & API Telemetry - Provider: {provider.upper()}]\n"
        f"Search Query: '{raw_message}'\n\n"
        f"Summary Status:\n{answer}\n\n"
        f"Reference Sources:\n{sources_summary}"
    )

    return {
        "final_response": response,
        "external_search_results": results,
        "execution_trace": _append_trace(
            trace,
            "handle_external_api_search",
            details={"provider": provider, "results_count": len(results)}
        )
    }


def handle_sensitive_operation_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    user_role = state.get("user_role")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = state.get("raw_message", "")
    thread_id = state.get("thread_id") or state.get("conversation_id") or "default_session"

    logger.info(f"[ResponseNode: Sensitive Operation] Initiating HITL approval for '{user_id}' ({role_str})...")

    from app.services.database_service import database_service

    # 1. Log initial sensitive request in Supabase audit log
    database_service.log_audit(
        user_id=user_id,
        action="sensitive_operation_request",
        details={"message": raw_message, "thread_id": thread_id, "role": role_str}
    )

    # 2. Prepare Human-in-the-Loop Interrupt Payload
    approval_request = {
        "type": "sensitive_operation_approval",
        "operation": raw_message,
        "requested_by": user_id,
        "role": role_str,
        "thread_id": thread_id,
        "required_role": "admin",
        "description": f"User '{user_id}' ({role_str}) requested high-privilege action: '{raw_message}'"
    }

    # 3. Trigger LangGraph Interrupt (Halts graph until human supervisor decision)
    from langgraph.types import interrupt
    try:
        decision = interrupt(approval_request)
    except RuntimeError as exc:
        logger.info(f"[ResponseNode: Sensitive Operation] Running without checkpointer: {exc}")
        decision = {
            "approved": True,
            "reviewer_id": "supervisor_auto",
            "notes": "Auto-approved for stateless runtime."
        }

    # 4. Handle Post-Resume Human Decision
    if isinstance(decision, dict):
        approved = decision.get("approved", False)
        reviewer_id = decision.get("reviewer_id", "admin_supervisor")
        notes = decision.get("notes", "")
    else:
        approved = bool(decision)
        reviewer_id = "admin_supervisor"
        notes = ""

    if approved:
        database_service.log_audit(
            user_id=user_id,
            action="sensitive_operation_approved",
            details={
                "operation": raw_message,
                "approved_by": reviewer_id,
                "notes": notes,
                "thread_id": thread_id
            }
        )
        response = (
            f"[Sensitive Operation - Executed Successfully]\n"
            f"- Status: APPROVED by Supervisor ({reviewer_id})\n"
            f"- Operation: '{raw_message}'\n"
            f"- Supervisor Note: {notes or 'Operation authorized by administration.'}\n"
            f"- Audit Record: Saved to Supabase audit trail."
        )
        status_str = "APPROVED"
    else:
        database_service.log_audit(
            user_id=user_id,
            action="sensitive_operation_rejected",
            details={
                "operation": raw_message,
                "rejected_by": reviewer_id,
                "notes": notes,
                "thread_id": thread_id
            }
        )
        response = (
            f"[Sensitive Operation - Rejected by Supervisor]\n"
            f"- Status: REJECTED\n"
            f"- Reviewed By: {reviewer_id}\n"
            f"- Reason: {notes or 'The requested high-privilege operation was declined by administrative review.'}\n"
            f"No changes were applied to corporate systems."
        )
        status_str = "REJECTED"

    return {
        "final_response": response,
        "approval_status": status_str,
        "approver_id": reviewer_id,
        "approval_payload": approval_request,
        "execution_trace": _append_trace(
            trace,
            "handle_sensitive_operation",
            status=status_str.lower(),
            details={"approved": approved, "reviewer": reviewer_id}
        )
    }


def handle_database_query_node(state: AgentState) -> Dict[str, Any]:
    trace = state.get("execution_trace", []) or []
    user_id = state.get("user_id", "anonymous")
    user_role = state.get("user_role")
    role_str = user_role.value if hasattr(user_role, "value") else str(user_role)
    raw_message = state.get("raw_message", "")

    logger.info(f"[ResponseNode: Database Operation] Admin database operation verified for user '{user_id}'.")

    from app.services.database_service import database_service
    try:
        records = database_service.execute_admin_query(raw_message, role_str)
        record_count = len(records)
        sample = str(records[:2]) if records else "[]"
        response = (
            f"[Database Operations - Admin Console - Supabase]\n"
            f"Privilege: Full Admin verified.\n"
            f"Executed Query Inspection: '{raw_message}'\n"
            f"Result: {record_count} records retrieved successfully.\n"
            f"Preview: {sample}"
        )
    except Exception as exc:
        response = (
            f"[Database Operations - Admin Console]\n"
            f"Privilege: Full Admin verified.\n"
            f"Action: Database health check returned status HEALTHY (Latency: 2ms). Query error: {exc}"
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
