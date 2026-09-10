from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict

from app.schemas.auth_schema import UserRole
from app.schemas.intent_schema import IntentType


class AgentState(TypedDict):
    # Core User & Auth Context
    user_id: str
    user_role: UserRole
    raw_message: str
    conversation_id: Optional[str]

    # Intent Classification Results
    intent: Optional[IntentType]
    confidence: Optional[float]
    reasoning: Optional[str]
    extracted_entities: Optional[List[str]]

    # Authorization & Guardrail State
    is_authorized: bool
    authorization_error: Optional[str]

    # Response & Execution Tracking
    final_response: Optional[str]
    execution_trace: List[Dict[str, Any]]
    error: Optional[str]

    # RAG & Context State (Phase 2)
    thread_id: Optional[str]
    retrieved_docs: Optional[List[Dict[str, Any]]]
    relevant_docs: Optional[List[Dict[str, Any]]]
    rag_sources: Optional[List[str]]
    retry_count: Optional[int]
    rewritten_query: Optional[str]

