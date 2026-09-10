from fastapi import APIRouter, Depends
from app.schemas.chat_schema import ChatRequest, ChatResponse, ExecutionStep
from app.schemas.auth_schema import UserProfile
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
    2. Intent Classification (7+ Intents)
    3. Intent Router (RBAC check against user role)
    4. Specialized Response generation
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
        execution_trace=execution_steps
    )

