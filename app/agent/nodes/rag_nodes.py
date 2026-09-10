from typing import Any, Dict, List
from datetime import datetime, timezone

from app.agent.state import AgentState
from app.core.logging import logger
from app.services.openrouter_embedding import embedding_service
from app.services.qdrant_cloud_service import qdrant_service
from app.services.llm_service import llm_service
from app.schemas.rag_schema import DocumentGrade, QueryRewrite
from app.agent.prompts.rag_prompts import (
    RAG_DOCUMENT_GRADER_SYSTEM_PROMPT,
    RAG_GROUNDED_GENERATION_SYSTEM_PROMPT,
    RAG_QUERY_REWRITER_SYSTEM_PROMPT
)


def _append_trace(trace: list, node_name: str, status: str = "success") -> list:
    trace = trace or []
    trace.append({
        "step_name": node_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": status
    })
    return trace


def rag_retrieve_node(state: AgentState) -> Dict[str, Any]:
    """Retrieve top matching chunks from Qdrant Cloud."""
    trace = state.get("execution_trace", []) or []
    # Use rewritten query if available from a previous loop, otherwise original message
    query = state.get("rewritten_query") or state.get("raw_message", "")
    logger.info(f"[RAG: Retrieve] Searching Qdrant Cloud for query: '{query}'")

    try:
        query_vector = embedding_service.embed_query(query)
        retrieved_docs = qdrant_service.similarity_search(query_vector=query_vector, top_k=4)
        docs_data = [doc.model_dump() for doc in retrieved_docs]
        
        return {
            "retrieved_docs": docs_data,
            "execution_trace": _append_trace(trace, "rag_retrieve")
        }
    except Exception as exc:
        logger.error(f"[RAG: Retrieve Error] Retrieval failed: {exc}")
        return {
            "retrieved_docs": [],
            "error": str(exc),
            "execution_trace": _append_trace(trace, "rag_retrieve", status="failed")
        }


def rag_grade_node(state: AgentState) -> Dict[str, Any]:
    """Grade retrieved documents for relevance to the user inquiry using similarity threshold and LLM."""
    trace = state.get("execution_trace", []) or []
    query = state.get("raw_message", "")
    retrieved_docs = state.get("retrieved_docs", []) or []
    
    logger.info(f"[RAG: Grade] Grading {len(retrieved_docs)} documents against query: '{query}'")
    relevant_docs: List[Dict[str, Any]] = []
    sources: List[str] = []

    # 1. Similarity score fast-track (0.42+ is high relevance for text-embedding-3-small cosine similarity)
    borderline_docs = []
    for doc in retrieved_docs:
        score = doc.get("score", 0.0)
        doc_name = doc.get("document_name", "unknown")
        section = doc.get("section_title", "Overview")
        source_tag = f"{doc_name} (Section: {section})"

        if score >= 0.42:
            relevant_docs.append(doc)
            if source_tag not in sources:
                sources.append(source_tag)
        elif score >= 0.32:
            borderline_docs.append((doc, source_tag))

    # 2. If no docs met the 0.42 threshold, evaluate the borderline docs
    if not relevant_docs and borderline_docs:
        for doc, source_tag in borderline_docs[:2]:
            content = doc.get("content", "")
            prompt = (
                f"Employee Query: {query}\n\n"
                f"Document Source: {source_tag}\n"
                f"Content Passage:\n{content}"
            )
            try:
                grade_result = llm_service.call_structured(
                    schema_cls=DocumentGrade,
                    prompt=prompt,
                    system_message=RAG_DOCUMENT_GRADER_SYSTEM_PROMPT
                )
                if grade_result.is_relevant:
                    relevant_docs.append(doc)
                    if source_tag not in sources:
                        sources.append(source_tag)
            except Exception as exc:
                logger.warning(f"[RAG: Grade] LLM grading failed, accepting top chunk: {exc}")
                relevant_docs.append(doc)
                if source_tag not in sources:
                    sources.append(source_tag)

    logger.info(f"[RAG: Grade] Filtered to {len(relevant_docs)} relevant documents. Sources: {sources}")
    return {
        "relevant_docs": relevant_docs,
        "rag_sources": sources,
        "execution_trace": _append_trace(trace, "rag_grade")
    }



def rag_generate_node(state: AgentState) -> Dict[str, Any]:
    """Generate grounded, source-attributed answer using LLM."""
    trace = state.get("execution_trace", []) or []
    query = state.get("raw_message", "")
    relevant_docs = state.get("relevant_docs", []) or []
    sources = state.get("rag_sources", []) or []

    logger.info(f"[RAG: Generate] Synthesizing grounded response from {len(relevant_docs)} passages.")

    # Build context string
    context_parts = []
    for idx, doc in enumerate(relevant_docs, 1):
        context_parts.append(
            f"--- Context Document {idx} ---\n"
            f"Source File: {doc.get('document_name')}\n"
            f"Section: {doc.get('section_title')}\n"
            f"Content:\n{doc.get('content')}\n"
        )
    combined_context = "\n".join(context_parts)

    user_prompt = (
        f"Employee Query: {query}\n\n"
        f"Approved Enterprise Knowledge Base Context:\n"
        f"{combined_context}\n\n"
        f"Please provide an accurate, step-by-step resolution based strictly on the context above."
    )

    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        messages = [
            SystemMessage(content=RAG_GROUNDED_GENERATION_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt)
        ]
        llm = llm_service.get_chat_model()
        response = llm.invoke(messages)
        final_answer = response.content if hasattr(response, "content") else str(response)

        return {
            "final_response": final_answer,
            "execution_trace": _append_trace(trace, "rag_generate")
        }
    except Exception as exc:
        logger.error(f"[RAG: Generate Error] Failed to generate response: {exc}")
        # Deterministic grounded fallback
        fallback_answer = (
            f"Based on our internal policies ({', '.join(sources) if sources else 'IT Knowledge Base'}):\n\n"
            f"{relevant_docs[0].get('content') if relevant_docs else 'Please review internal IT documentation.'}\n\n"
            f"**Sources & References:**\n" +
            "\n".join([f"- {src}" for src in sources])
        )
        return {
            "final_response": fallback_answer,
            "execution_trace": _append_trace(trace, "rag_generate", status="fallback")
        }


def rag_rewrite_node(state: AgentState) -> Dict[str, Any]:
    """Rewrite query with technical terminology for second-chance retrieval loop."""
    trace = state.get("execution_trace", []) or []
    query = state.get("raw_message", "")
    retry_count = state.get("retry_count", 0) or 0

    logger.info(f"[RAG: Rewrite] Reformulating query (Attempt {retry_count + 1}): '{query}'")

    prompt = f"Original Employee Query: '{query}'"
    try:
        rewrite_result = llm_service.call_structured(
            schema_cls=QueryRewrite,
            prompt=prompt,
            system_message=RAG_QUERY_REWRITER_SYSTEM_PROMPT
        )
        rewritten = rewrite_result.rewritten_query
        logger.info(f"[RAG: Rewrite] New search query: '{rewritten}' (Rationale: {rewrite_result.rationale})")
    except Exception as exc:
        logger.warning(f"[RAG: Rewrite] LLM query rewrite failed, using keyword fallback: {exc}")
        rewritten = f"{query} enterprise IT policy configuration guide"

    return {
        "rewritten_query": rewritten,
        "retry_count": retry_count + 1,
        "execution_trace": _append_trace(trace, "rag_rewrite")
    }


def rag_fallback_node(state: AgentState) -> Dict[str, Any]:
    """Graceful fallback when no documentation answers the user request."""
    trace = state.get("execution_trace", []) or []
    query = state.get("raw_message", "")
    logger.info(f"[RAG: Fallback] No knowledge base match found for: '{query}'")

    response = (
        "I searched our enterprise knowledge base, but could not find specific documentation "
        "or policies addressing your request. "
        "To help you resolve this issue, you may create a support ticket by saying "
        "'Create a new support ticket' or contact our IT Helpdesk directly."
    )
    return {
        "final_response": response,
        "execution_trace": _append_trace(trace, "rag_fallback")
    }
