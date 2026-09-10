from fastapi import APIRouter, Depends
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
    current_user: UserProfile = Depends(get_current_user)
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
        "execution_trace": []
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
            ]
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
        execution_trace=execution_steps
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

