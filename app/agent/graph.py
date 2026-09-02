from langgraph.graph import StateGraph, START, END

from app.agent.state import AgentState
from app.agent.nodes.receive_node import receive_message_node
from app.agent.nodes.classify_node import classify_intent_node
from app.agent.nodes.router_node import intent_router_node
from app.agent.nodes.response_nodes import (
    handle_greeting_node,
    handle_knowledge_search_node,
    handle_my_tickets_search_node,
    handle_ticket_create_update_node,
    handle_external_api_search_node,
    handle_sensitive_operation_node,
    handle_database_query_node,
    handle_unauthorized_node,
    handle_fallback_node
)
from app.agent.edges.routing_rules import route_after_rbac_check


def build_enterprise_support_graph():
    """
    Constructs and compiles the Phase 1 LangGraph workflow.
    """
    builder = StateGraph(AgentState)

    # 1. Register Core Workflow Nodes
    builder.add_node("receive_message", receive_message_node)
    builder.add_node("classify_intent", classify_intent_node)
    builder.add_node("router_node", intent_router_node)

    # 2. Register Response Handler Nodes
    builder.add_node("handle_greeting", handle_greeting_node)
    builder.add_node("handle_knowledge_search", handle_knowledge_search_node)
    builder.add_node("handle_my_tickets_search", handle_my_tickets_search_node)
    builder.add_node("handle_ticket_create_update", handle_ticket_create_update_node)
    builder.add_node("handle_external_api_search", handle_external_api_search_node)
    builder.add_node("handle_sensitive_operation", handle_sensitive_operation_node)
    builder.add_node("handle_database_query", handle_database_query_node)
    builder.add_node("handle_unauthorized", handle_unauthorized_node)
    builder.add_node("handle_fallback", handle_fallback_node)

    # 3. Add Sequential Edges
    builder.add_edge(START, "receive_message")
    builder.add_edge("receive_message", "classify_intent")
    builder.add_edge("classify_intent", "router_node")

    # 4. Add Conditional Routing Edges
    builder.add_conditional_edges(
        "router_node",
        route_after_rbac_check,
        {
            "handle_greeting": "handle_greeting",
            "handle_knowledge_search": "handle_knowledge_search",
            "handle_my_tickets_search": "handle_my_tickets_search",
            "handle_ticket_create_update": "handle_ticket_create_update",
            "handle_external_api_search": "handle_external_api_search",
            "handle_sensitive_operation": "handle_sensitive_operation",
            "handle_database_query": "handle_database_query",
            "handle_unauthorized": "handle_unauthorized",
            "handle_fallback": "handle_fallback"
        }
    )

    # 5. Connect all terminal response nodes to END
    builder.add_edge("handle_greeting", END)
    builder.add_edge("handle_knowledge_search", END)
    builder.add_edge("handle_my_tickets_search", END)
    builder.add_edge("handle_ticket_create_update", END)
    builder.add_edge("handle_external_api_search", END)
    builder.add_edge("handle_sensitive_operation", END)
    builder.add_edge("handle_database_query", END)
    builder.add_edge("handle_unauthorized", END)
    builder.add_edge("handle_fallback", END)

    return builder.compile()


# Singleton compiled graph instance
enterprise_agent_graph = build_enterprise_support_graph()
