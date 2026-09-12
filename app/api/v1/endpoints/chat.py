import json
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse
from app.schemas.chat_schema import ChatRequest, ChatResponse, ExecutionStep, ApprovalDecisionRequest
from app.schemas.auth_schema import UserProfile, UserRole
from app.schemas.intent_schema import IntentType
from app.api.dependencies import get_current_user
from app.agent.graph import enterprise_agent_graph
from app.core.logging import logger

router = APIRouter(prefix="/chat", tags=["Agent Chat"])


@router.post("", response_model=ChatResponse, summary="Send a message to the Enterprise Support Agent")
async def send_chat_message(
    body: ChatRequest,
    current_user: UserProfile = Depends(get_current_user),
    x_bypass_cache: Optional[str] = Header(default=None)
):
    """
    Executes the LangGraph workflow:
    1. Receive Message
    2. Intent Classification (8 Intents)
    3. Intent Router (RBAC check against user role)
    4. Specialized Response generation / Agentic RAG / External API / HITL Interrupt
    """
    logger.info(f"[API: /chat] User '{current_user.id}' ({current_user.role.value}) sent: '{body.message}'")

    # Extract or generate persistent thread identifier
    thread_id = body.thread_id or body.conversation_id or f"thread_{current_user.id}"

    # Initial graph state input
    initial_state = {
        "user_id": current_user.id,
        "user_role": current_user.role,
        "raw_message": body.message,
        "conversation_id": thread_id,
        "thread_id": thread_id,
        "execution_trace": [],
        "bypass_cache": bool(x_bypass_cache and x_bypass_cache.lower() == "true")
    }

    # Execute graph with thread-level persistence configuration
    config = {"configurable": {"thread_id": thread_id}}
    final_state = enterprise_agent_graph.invoke(initial_state, config=config)

    # Check if graph halted on a Human-in-the-Loop Interrupt
    interrupts = final_state.get("__interrupt__")
    if interrupts:
        interrupt_val = interrupts[0].value if hasattr(interrupts[0], "value") else interrupts[0]
        logger.info(f"[API: /chat] Graph paused at HITL interrupt for thread '{thread_id}'")

        return ChatResponse(
            response=(
                f"[APPROVAL REQUIRED - SENSITIVE OPERATION]\n"
                f"This high-privilege action requires supervisor or administrative approval.\n"
                f"- Thread ID: {thread_id}\n"
                f"- Operation: '{body.message}'\n"
                f"- Status: PENDING_SUPERVISOR_APPROVAL\n"
                f"A supervisor can approve or reject via POST /api/v1/chat/approvals/{thread_id}/decide"
            ),
            intent=final_state.get("intent", IntentType.SENSITIVE_OPERATION),
            confidence=final_state.get("confidence", 1.0),
            user_role=current_user.role,
            is_authorized=final_state.get("is_authorized", True),
            conversation_id=thread_id,
            thread_id=thread_id,
            approval_required=True,
            approval_status="PENDING",
            approval_details=interrupt_val if isinstance(interrupt_val, dict) else {"details": str(interrupt_val)},
            sources=[],
            execution_trace=[
                ExecutionStep(
                    step_name=step.get("step_name", "unknown"),
                    status=step.get("status", "success"),
                    details=step.get("details")
                )
                for step in final_state.get("execution_trace", [])
            ],
            cached=False,
            cache_score=None
        )

    execution_steps = [
        ExecutionStep(
            step_name=step.get("step_name", "unknown"),
            status=step.get("status", "success"),
            details=step.get("details")
        )
        for step in final_state.get("execution_trace", [])
    ]

    return ChatResponse(
        response=final_state.get("final_response", "No response generated."),
        intent=final_state.get("intent", IntentType.OUT_OF_SCOPE),
        confidence=final_state.get("confidence", 1.0),
        user_role=current_user.role,
        is_authorized=final_state.get("is_authorized", True),
        conversation_id=thread_id,
        thread_id=thread_id,
        sources=final_state.get("rag_sources", []) or [],
        external_results=final_state.get("external_search_results"),
        approval_status=final_state.get("approval_status"),
        approval_required=False,
        execution_trace=execution_steps,
        cached=bool(final_state.get("cached", False)),
        cache_score=final_state.get("cache_score")
    )


@router.post(
    "/stream",
    summary="Stream message execution, agent thoughts, and response tokens via Server-Sent Events (SSE)"
)
async def stream_chat_message(
    body: ChatRequest,
    current_user: UserProfile = Depends(get_current_user),
    x_bypass_cache: Optional[str] = Header(default=None)
):
    """
    Phase 7: Real-Time Token & Agent Reasoning Streaming (Server-Sent Events - SSE):
    Streams graph node progression, pedagogical agent thoughts, and token chunks.
    Phase 9: Seamlessly returns cached answers (< 25ms) with 'cached: true' when available.
    """
    logger.info(f"[API: /chat/stream] User '{current_user.id}' ({current_user.role.value}) requested stream: '{body.message}'")
    thread_id = body.thread_id or body.conversation_id or f"thread_{current_user.id}"

    initial_state = {
        "user_id": current_user.id,
        "user_role": current_user.role,
        "raw_message": body.message,
        "conversation_id": thread_id,
        "thread_id": thread_id,
        "execution_trace": [],
        "bypass_cache": bool(x_bypass_cache and x_bypass_cache.lower() == "true")
    }
    config = {"configurable": {"thread_id": thread_id}}

    async def event_generator():
        try:
            # 1. Initial connect handshake event
            yield f"event: step\ndata: {json.dumps({'step': 'start', 'status': 'connected', 'thread_id': thread_id})}\n\n"

            final_state = {}
            stream_iterator = enterprise_agent_graph.stream(initial_state, config=config, stream_mode="updates")

            for event in stream_iterator:
                for node_name, node_output in event.items():
                    # Handle LangGraph HITL interrupt
                    if node_name == "__interrupt__":
                        interrupt_val = node_output[0].value if hasattr(node_output[0], "value") else node_output[0]
                        interrupt_payload = {
                            "approval_required": True,
                            "thread_id": thread_id,
                            "status": "PENDING_SUPERVISOR_APPROVAL",
                            "details": interrupt_val if isinstance(interrupt_val, dict) else {"details": str(interrupt_val)}
                        }
                        yield f"event: interrupt\ndata: {json.dumps(interrupt_payload)}\n\n"
                        yield f"event: done\ndata: {json.dumps({'final_response': 'Approval required for sensitive operation.', 'approval_required': True, 'thread_id': thread_id, 'approval_status': 'PENDING', 'cached': False})}\n\n"
                        return

                    final_state.update(node_output)

                    # Pedagogical agent thoughts mapping
                    thought_map = {
                        "receive_message": "Message received and validated.",
                        "semantic_cache_check": "Checking vector semantic cache for previous answers...",
                        "classify_intent": f"Classified intent as '{node_output.get('intent', 'unknown')}'.",
                        "router_node": "Verifying role-based permissions (RBAC)...",
                        "handle_greeting": "Synthesizing welcoming greeting...",
                        "rag_retrieve": "Searching enterprise knowledge base...",
                        "rag_grade": "Grading relevance of retrieved documents...",
                        "rag_rewrite": "Refining search query for better document retrieval...",
                        "rag_generate": "Formulating grounded answer with citations...",
                        "rag_fallback": "Applying enterprise fallback response...",
                        "handle_my_tickets_search": "Fetching user support tickets from database...",
                        "handle_ticket_create_update": "Executing ticket creation in database...",
                        "handle_external_api_search": "Querying external search and status API...",
                        "handle_sensitive_operation": "Evaluating sensitive operation permissions...",
                        "handle_database_query": "Executing diagnostic database query...",
                        "handle_unauthorized": "Access denied: User lacks required role permissions.",
                        "handle_fallback": "Synthesizing fallback response."
                    }
                    thought_msg = thought_map.get(node_name, f"Completed node: {node_name}")

                    def _clean_intent(val):
                        if val is None:
                            return None
                        if hasattr(val, "value"):
                            return val.value
                        s = str(val)
                        return s.split(".")[-1].lower() if "IntentType." in s else s

                    step_payload = {
                        "node": node_name,
                        "status": "completed",
                        "thought": thought_msg,
                        "intent": _clean_intent(node_output.get("intent")),
                        "is_authorized": node_output.get("is_authorized", True)
                    }
                    yield f"event: step\ndata: {json.dumps(step_payload)}\n\n"
                    yield f"event: thought\ndata: {json.dumps({'thought': thought_msg})}\n\n"

                    # Stream tokens if final_response was generated in this node
                    if "final_response" in node_output and node_output["final_response"]:
                        response_text = node_output["final_response"]
                        words = response_text.split(" ")
                        for i, word in enumerate(words):
                            token_chunk = word + (" " if i < len(words) - 1 else "")
                            yield f"event: token\ndata: {json.dumps({'token': token_chunk})}\n\n"
                            await asyncio.sleep(0.01)

            # Emit final done event with full context
            done_payload = {
                "final_response": final_state.get("final_response", ""),
                "intent": _clean_intent(final_state.get("intent", "out_of_scope")),
                "is_authorized": final_state.get("is_authorized", True),
                "thread_id": thread_id,
                "sources": final_state.get("rag_sources", []) or [],
                "external_results": final_state.get("external_search_results"),
                "approval_required": False,
                "approval_status": final_state.get("approval_status"),
                "cached": bool(final_state.get("cached", False)),
                "cache_score": final_state.get("cache_score")
            }
            yield f"event: done\ndata: {json.dumps(done_payload)}\n\n"

        except Exception as exc:
            logger.error(f"[API: /chat/stream] Streaming error: {exc}")
            yield f"event: error\ndata: {json.dumps({'error': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Content-Type": "text/event-stream"
        }
    )


@router.post(
    "/approvals/{thread_id}/decide",
    response_model=ChatResponse,
    summary="Supervisor Human-in-the-Loop decision to approve or reject a paused sensitive operation"
)
async def decide_sensitive_operation(
    thread_id: str,
    decision_body: ApprovalDecisionRequest,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Supervisor endpoint for Human-in-the-Loop workflows (Phase 4):
    Resumes a paused LangGraph thread using Command(resume=decision).
    Only Senior Agent and Admin roles are authorized to approve or reject operations.
    """
    from fastapi import HTTPException, status
    from langgraph.types import Command

    # RBAC Check: Only Senior Agent or Admin can approve/reject
    if current_user.role not in [UserRole.SENIOR_AGENT, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Senior Agents or Administrators can review and decide sensitive operations."
        )

    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = enterprise_agent_graph.get_state(config)

    if not state_snapshot.next:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No pending approval found for thread '{thread_id}'. The thread is not currently paused."
        )

    logger.info(
        f"[API: /approvals] Supervisor '{current_user.id}' ({current_user.role.value}) "
        f"{'APPROVED' if decision_body.approved else 'REJECTED'} thread '{thread_id}'"
    )

    decision_payload = {
        "approved": decision_body.approved,
        "reviewer_id": current_user.id,
        "reviewer_role": current_user.role.value,
        "notes": decision_body.reviewer_notes
    }

    # Resume the paused LangGraph workflow with supervisor's decision
    resumed_state = enterprise_agent_graph.invoke(
        Command(resume=decision_payload),
        config=config
    )

    execution_steps = [
        ExecutionStep(
            step_name=step.get("step_name", "unknown"),
            status=step.get("status", "success"),
            details=step.get("details")
        )
        for step in resumed_state.get("execution_trace", [])
    ]

    return ChatResponse(
        response=resumed_state.get("final_response", "Resumed execution finished."),
        intent=resumed_state.get("intent", IntentType.SENSITIVE_OPERATION),
        confidence=resumed_state.get("confidence", 1.0),
        user_role=current_user.role,
        is_authorized=resumed_state.get("is_authorized", True),
        conversation_id=thread_id,
        thread_id=thread_id,
        sources=[],
        approval_required=False,
        approval_status=resumed_state.get("approval_status"),
        approval_details={"resumed_by": current_user.id, "approved": decision_body.approved},
        execution_trace=execution_steps
    )


@router.get(
    "/approvals/{thread_id}/status",
    summary="Check if a thread is currently awaiting Human-in-the-Loop supervisor approval"
)
async def get_approval_status(
    thread_id: str,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Returns whether the specified thread is waiting on an interrupt.
    """
    config = {"configurable": {"thread_id": thread_id}}
    state_snapshot = enterprise_agent_graph.get_state(config)

    is_pending = bool(state_snapshot.next)
    interrupts = []
    if hasattr(state_snapshot, "tasks") and state_snapshot.tasks:
        for t in state_snapshot.tasks:
            if hasattr(t, "interrupts"):
                interrupts.extend([i.value for i in t.interrupts])

    return {
        "thread_id": thread_id,
        "is_pending_approval": is_pending,
        "next_nodes": list(state_snapshot.next),
        "interrupts": interrupts
    }

