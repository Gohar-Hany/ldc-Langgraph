from typing import Any, Dict
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.config import settings
from app.core.logging import logger
from app.schemas.intent_schema import IntentType
from app.services.semantic_cache_service import semantic_cache_service
from app.services.metrics_service import metrics_service


def semantic_cache_check_node(state: AgentState) -> Dict[str, Any]:
    """
    LangGraph Vector Semantic Cache Gateway Node (Phase 9):
    Inspects Qdrant semantic cache before executing expensive intent classification or RAG.
    If a semantically similar query exists (Cosine Similarity >= 0.92):
        Short-circuits execution directly to final response with cached: True (< 25ms).
    Otherwise:
        Routes forward to classify_intent node.
    """
    trace = state.get("execution_trace", []) or []

    # 1. Bypass cache if security violation is detected (attacks must not read or populate cache)
    if state.get("security_flag") == "PROMPT_INJECTION_DETECTED":
        return {
            "cached": False,
            "cache_score": None
        }

    # 2. Check if cache is explicitly bypassed via header/state or disabled globally
    if state.get("bypass_cache", False) or not settings.SEMANTIC_CACHE_ENABLED:
        trace.append({
            "step_name": "semantic_cache_lookup",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "bypassed",
            "details": {"reason": "Cache explicitly bypassed or disabled"}
        })
        return {
            "cached": False,
            "cache_score": None,
            "execution_trace": trace
        }

    query = (state.get("sanitized_message") or state.get("raw_message", "")).strip()
    raw_role = state.get("user_role", "customer")
    role_str = raw_role.value if hasattr(raw_role, "value") else str(raw_role)

    hit = semantic_cache_service.lookup(query, role_str)

    if hit:
        metrics_service.record_cache_hit()
        logger.info(f"[CacheNode: HIT] Found semantic match for '{query[:40]}' (score: {hit.similarity_score:.4f})")

        try:
            matched_intent = IntentType(hit.intent)
        except ValueError:
            matched_intent = IntentType.KNOWLEDGE_SEARCH

        trace.append({
            "step_name": "semantic_cache_lookup",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "cache_hit",
            "details": {
                "similarity_score": hit.similarity_score,
                "cached_query": hit.query,
                "intent": hit.intent,
                "sources_count": len(hit.sources)
            }
        })

        return {
            "cached": True,
            "cache_score": hit.similarity_score,
            "final_response": hit.response,
            "intent": matched_intent,
            "rag_sources": hit.sources,
            "confidence": 1.0,
            "is_authorized": True,
            "authorization_error": None,
            "execution_trace": trace
        }
    else:
        metrics_service.record_cache_miss()
        logger.info(f"[CacheNode: MISS] No semantic cache match for '{query[:40]}'")

        trace.append({
            "step_name": "semantic_cache_lookup",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "cache_miss",
            "details": {"query_checked": query}
        })

        return {
            "cached": False,
            "cache_score": None,
            "execution_trace": trace
        }
