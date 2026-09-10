from app.agent.state import AgentState
from app.core.logging import logger


def decide_rag_flow(state: AgentState) -> str:
    """Determine whether to proceed to generation, rewrite query in loop, or fallback."""
    relevant_docs = state.get("relevant_docs", []) or []
    retry_count = state.get("retry_count", 0) or 0

    if len(relevant_docs) > 0:
        logger.info(f"[RAG: Edge] Found {len(relevant_docs)} relevant docs -> routing to 'generate'.")
        return "generate"
    elif retry_count < 1:
        logger.info(f"[RAG: Edge] 0 relevant docs (retry_count={retry_count}) -> routing to 'rewrite' query loop.")
        return "rewrite"
    else:
        logger.info(f"[RAG: Edge] Max retries reached with 0 relevant docs -> routing to 'fallback'.")
        return "fallback"
