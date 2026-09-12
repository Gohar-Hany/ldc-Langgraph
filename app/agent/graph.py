from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from app.agent.state import AgentState
from app.agent.nodes.receive_node import receive_message_node
from app.agent.nodes.classify_node import classify_intent_node
from app.agent.nodes.router_node import intent_router_node
from app.agent.nodes.response_nodes import (
    handle_greeting_node,
    handle_my_tickets_search_node,
    handle_ticket_create_update_node,
    handle_external_api_search_node,
    handle_sensitive_operation_node,
    handle_database_query_node,
    handle_unauthorized_node,
    handle_fallback_node
)
from app.agent.nodes.rag_nodes import (
    rag_retrieve_node,
    rag_grade_node,
    rag_generate_node,
    rag_rewrite_node,
    rag_fallback_node
)
from app.agent.nodes.cache_node import semantic_cache_check_node
from app.agent.edges.routing_rules import route_after_rbac_check, route_after_cache_check
from app.agent.edges.rag_edges import decide_rag_flow


from app.core.config import settings
from app.core.logging import logger

def init_checkpointer():
    """
    Initializes the enterprise LangGraph checkpointer.
    If CHECKPOINTER_BACKEND is 'postgres' and DATABASE_URL is configured:
        Connects via PostgreSQL ConnectionPool and sets up checkpoint tables.
    Otherwise or on connection failure:
        Falls back gracefully to in-memory MemorySaver with logging.
    """
    if settings.CHECKPOINTER_BACKEND == "postgres" and settings.DATABASE_URL:
        try:
            from psycopg_pool import ConnectionPool
            from psycopg.rows import dict_row
            from langgraph.checkpoint.postgres import PostgresSaver

            redacted_url = settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else "configured host"
            logger.info(f"[Checkpointer] Connecting to persistent PostgreSQL checkpointer at {redacted_url}")

            pool = ConnectionPool(
                settings.DATABASE_URL,
                open=True,
                max_size=10,
                timeout=5.0,
                kwargs={"autocommit": True, "prepare_threshold": 0, "row_factory": dict_row}
            )
            # Enterprise Health Ping: Verify connectivity with non-DDL SELECT 1
            # Guarantees connection works without executing any schema mutations at runtime.
            with pool.connection(timeout=3.0) as conn:
                conn.execute("SELECT 1;")

            saver = PostgresSaver(pool)
            logger.info("[Checkpointer] Successfully connected and verified persistent PostgresSaver.")
            return saver
        except Exception as e:
            logger.warning(f"[Checkpointer] Failed to initialize PostgresSaver ({e}). Falling back to MemorySaver.")
            return MemorySaver()

    return MemorySaver()


# Shared checkpointer instance for state persistence across conversation threads
checkpointer = init_checkpointer()


def set_checkpointer(new_checkpointer):
    """Allows dynamic test injection or backend switching."""
    global checkpointer, enterprise_agent_graph
    checkpointer = new_checkpointer
    enterprise_agent_graph = build_enterprise_support_graph(use_checkpointer=True, custom_checkpointer=new_checkpointer)
    return enterprise_agent_graph


def build_enterprise_support_graph(use_checkpointer: bool = True, custom_checkpointer=None):
    """
    Constructs and compiles the enterprise LangGraph workflow with Agentic RAG
    and persistent conversation state checkpointing.
    """
    builder = StateGraph(AgentState)

    # 1. Core Workflow Nodes
    builder.add_node("receive_message", receive_message_node)
    builder.add_node("semantic_cache_check", semantic_cache_check_node)
    builder.add_node("classify_intent", classify_intent_node)
    builder.add_node("router_node", intent_router_node)

    # 2. Phase 1 Static Handlers
    builder.add_node("handle_greeting", handle_greeting_node)
    builder.add_node("handle_my_tickets_search", handle_my_tickets_search_node)
    builder.add_node("handle_ticket_create_update", handle_ticket_create_update_node)
    builder.add_node("handle_external_api_search", handle_external_api_search_node)
    builder.add_node("handle_sensitive_operation", handle_sensitive_operation_node)
    builder.add_node("handle_database_query", handle_database_query_node)
    builder.add_node("handle_unauthorized", handle_unauthorized_node)
    builder.add_node("handle_fallback", handle_fallback_node)

    # 3. Phase 2 Agentic RAG Pipeline Nodes
    builder.add_node("rag_retrieve", rag_retrieve_node)
    builder.add_node("rag_grade", rag_grade_node)
    builder.add_node("rag_generate", rag_generate_node)
    builder.add_node("rag_rewrite", rag_rewrite_node)
    builder.add_node("rag_fallback", rag_fallback_node)

    # 4. Entry, Vector Semantic Caching, and Intent Classification Flow
    builder.add_edge(START, "receive_message")
    builder.add_edge("receive_message", "semantic_cache_check")
    builder.add_conditional_edges(
        "semantic_cache_check",
        route_after_cache_check,
        {
            "cache_hit": END,
            "cache_miss": "classify_intent"
        }
    )
    builder.add_edge("classify_intent", "router_node")

    # 5. RBAC Router Conditional Edges
    builder.add_conditional_edges(
        "router_node",
        route_after_rbac_check,
        {
            "handle_greeting": "handle_greeting",
            "handle_knowledge_search": "rag_retrieve",  # Routes to Agentic RAG pipeline
            "handle_my_tickets_search": "handle_my_tickets_search",
            "handle_ticket_create_update": "handle_ticket_create_update",
            "handle_external_api_search": "handle_external_api_search",
            "handle_sensitive_operation": "handle_sensitive_operation",
            "handle_database_query": "handle_database_query",
            "handle_unauthorized": "handle_unauthorized",
            "handle_fallback": "handle_fallback"
        }
    )

    # 6. Agentic RAG Flow with Self-Correction Loop
    builder.add_edge("rag_retrieve", "rag_grade")
    builder.add_conditional_edges(
        "rag_grade",
        decide_rag_flow,
        {
            "generate": "rag_generate",
            "rewrite": "rag_rewrite",
            "fallback": "rag_fallback"
        }
    )
    # Loop: Query rewriter routes back to retrieve
    builder.add_edge("rag_rewrite", "rag_retrieve")

    # 7. Terminal Nodes to END
    builder.add_edge("rag_generate", END)
    builder.add_edge("rag_fallback", END)
    builder.add_edge("handle_greeting", END)
    builder.add_edge("handle_my_tickets_search", END)
    builder.add_edge("handle_ticket_create_update", END)
    builder.add_edge("handle_external_api_search", END)
    builder.add_edge("handle_sensitive_operation", END)
    builder.add_edge("handle_database_query", END)
    builder.add_edge("handle_unauthorized", END)
    builder.add_edge("handle_fallback", END)

    if use_checkpointer:
        active_cp = custom_checkpointer if custom_checkpointer is not None else checkpointer
        return builder.compile(checkpointer=active_cp)
    return builder.compile()


# Singleton compiled graph instance with state persistence
enterprise_agent_graph = build_enterprise_support_graph(use_checkpointer=True)
