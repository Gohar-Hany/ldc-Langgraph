from app.agent.nodes.router_node import intent_router_node
from app.agent.edges.routing_rules import route_after_rbac_check
from app.schemas.auth_schema import UserRole
from app.schemas.intent_schema import IntentType


def test_customer_permissions():
    # Customer allowed
    state_kb = {"user_role": UserRole.CUSTOMER, "intent": IntentType.KNOWLEDGE_SEARCH, "execution_trace": []}
    result_kb = intent_router_node(state_kb)
    assert result_kb["is_authorized"] is True

    # Customer forbidden from database
    state_db = {"user_role": UserRole.CUSTOMER, "intent": IntentType.DATABASE_QUERY_OPERATION, "execution_trace": []}
    result_db = intent_router_node(state_db)
    assert result_db["is_authorized"] is False
    assert "Access Denied" in result_db["authorization_error"]

    # Customer forbidden from sensitive operations
    state_sen = {"user_role": UserRole.CUSTOMER, "intent": IntentType.SENSITIVE_OPERATION, "execution_trace": []}
    result_sen = intent_router_node(state_sen)
    assert result_sen["is_authorized"] is False


def test_support_agent_permissions():
    # Support agent can manage tickets and external APIs
    state_ticket = {"user_role": UserRole.SUPPORT_AGENT, "intent": IntentType.TICKET_CREATE_UPDATE, "execution_trace": []}
    assert intent_router_node(state_ticket)["is_authorized"] is True

    state_api = {"user_role": UserRole.SUPPORT_AGENT, "intent": IntentType.EXTERNAL_API_SEARCH, "execution_trace": []}
    assert intent_router_node(state_api)["is_authorized"] is True

    # Support agent cannot execute sensitive operations or db operations
    state_sensitive = {"user_role": UserRole.SUPPORT_AGENT, "intent": IntentType.SENSITIVE_OPERATION, "execution_trace": []}
    assert intent_router_node(state_sensitive)["is_authorized"] is False


def test_senior_agent_permissions():
    # Senior agent can execute sensitive operations
    state_sensitive = {"user_role": UserRole.SENIOR_AGENT, "intent": IntentType.SENSITIVE_OPERATION, "execution_trace": []}
    assert intent_router_node(state_sensitive)["is_authorized"] is True

    # Senior agent cannot execute direct db operations
    state_db = {"user_role": UserRole.SENIOR_AGENT, "intent": IntentType.DATABASE_QUERY_OPERATION, "execution_trace": []}
    assert intent_router_node(state_db)["is_authorized"] is False


def test_admin_full_permissions():
    # Admin is authorized for everything including database operations
    for intent in IntentType:
        state = {"user_role": UserRole.ADMIN, "intent": intent, "execution_trace": []}
        assert intent_router_node(state)["is_authorized"] is True


def test_conditional_routing_edge():
    # Authorized routes to specific node
    state_auth = {"is_authorized": True, "intent": IntentType.GREETING}
    assert route_after_rbac_check(state_auth) == "handle_greeting"

    # Unauthorized routes to handle_unauthorized
    state_unauth = {"is_authorized": False, "intent": IntentType.DATABASE_QUERY_OPERATION}
    assert route_after_rbac_check(state_unauth) == "handle_unauthorized"
