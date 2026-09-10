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
from app.agent.edges.routing_rules import route_after_rbac_check
from app.agent.edges.rag_edges import decide_rag_flow


# Shared checkpointer instance for state persistence across conversation threads
checkpointer = MemorySaver()


def build_enterprise_support_graph(use_checkpointer: bool = True):
    """
    Constructs and compiles the enterprise LangGraph workflow with Agentic RAG
    and persistent conversation state checkpointing.
    """
    builder = StateGraph(AgentState)

    # 1. Core Workflow Nodes
    builder.add_node("receive_message", receive_message_node)
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

    # 4. Entry and Intent Classification Flow
    builder.add_edge(START, "receive_message")
    builder.add_edge("receive_message", "classify_intent")
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
        return builder.compile(checkpointer=checkpointer)
    return builder.compile()


# Singleton compiled graph instance with state persistence
enterprise_agent_graph = build_enterprise_support_graph(use_checkpointer=True)
