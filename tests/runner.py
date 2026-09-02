import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.llm_service import llm_service
from app.schemas.intent_schema import IntentType
from app.agent.nodes.router_node import intent_router_node
from app.agent.edges.routing_rules import route_after_rbac_check
from app.schemas.auth_schema import UserRole
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password
from app.agent.graph import enterprise_agent_graph


def run_all_tests():
    print("=== [1/4] Running Security & Token Tests ===")
    pwd = "EnterprisePassword123"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed), "Password verification failed"
    assert not verify_password("wrong", hashed), "Wrong password check failed"
    
    token = create_access_token(subject="test_user", role=UserRole.ADMIN.value)
    payload = decode_access_token(token)
    assert payload["sub"] == "test_user" and payload["role"] == "admin", "Token payload mismatch"
    print("Security & Token tests passed.")

    print("\n=== [2/4] Running Intent Classification (8 Intents) Tests ===")
    test_cases = [
        ("Hello, good morning!", IntentType.GREETING),
        ("Hi there, how are you?", IntentType.GREETING),
        ("مرحبا، السلام عليكم", IntentType.GREETING),
        ("How to configure corporate VPN?", IntentType.KNOWLEDGE_SEARCH),
        ("Check my ticket status #1042", IntentType.MY_TICKETS_SEARCH),
        ("Create a new support ticket for email outage", IntentType.TICKET_CREATE_UPDATE),
        ("Query external API for vendor status", IntentType.EXTERNAL_API_SEARCH),
        ("Reset password for user John", IntentType.SENSITIVE_OPERATION),
        ("Run SQL database query on users table", IntentType.DATABASE_QUERY_OPERATION),
        ("What is the capital of Canada?", IntentType.OUT_OF_SCOPE)
    ]
    for text, expected in test_cases:
        res = llm_service.classify_intent_fallback(text)
        assert res.intent == expected, f"Failed for '{text}': expected {expected}, got {res.intent}"
        print(f"PASS: '{text[:35]}...' -> {res.intent.value} (conf: {res.confidence})")
    print("All 8 Intents successfully classified.")

    print("\n=== [3/4] Running RBAC Router & Authorization Tests ===")
    # Customer allowed on knowledge search
    r1 = intent_router_node({"user_role": UserRole.CUSTOMER, "intent": IntentType.KNOWLEDGE_SEARCH, "execution_trace": []})
    assert r1["is_authorized"] is True
    
    # Customer forbidden on database
    r2 = intent_router_node({"user_role": UserRole.CUSTOMER, "intent": IntentType.DATABASE_QUERY_OPERATION, "execution_trace": []})
    assert r2["is_authorized"] is False
    
    # Support agent allowed on tickets, forbidden on sensitive
    r3 = intent_router_node({"user_role": UserRole.SUPPORT_AGENT, "intent": IntentType.TICKET_CREATE_UPDATE, "execution_trace": []})
    assert r3["is_authorized"] is True
    r4 = intent_router_node({"user_role": UserRole.SUPPORT_AGENT, "intent": IntentType.SENSITIVE_OPERATION, "execution_trace": []})
    assert r4["is_authorized"] is False
    
    # Senior agent allowed on sensitive
    r5 = intent_router_node({"user_role": UserRole.SENIOR_AGENT, "intent": IntentType.SENSITIVE_OPERATION, "execution_trace": []})
    assert r5["is_authorized"] is True
    
    # Admin allowed on everything
    r6 = intent_router_node({"user_role": UserRole.ADMIN, "intent": IntentType.DATABASE_QUERY_OPERATION, "execution_trace": []})
    assert r6["is_authorized"] is True
    print("RBAC matrix permission tests passed.")

    print("\n=== [4/4] Running End-to-End LangGraph Workflow Tests ===")
    # Test Graph Execution for Customer
    state_cust = {
        "user_id": "cust_123",
        "user_role": UserRole.CUSTOMER,
        "raw_message": "How to configure corporate VPN?",
        "conversation_id": "test_conv_01",
        "execution_trace": []
    }
    out_cust = enterprise_agent_graph.invoke(state_cust)
    assert out_cust["is_authorized"] is True
    assert out_cust["intent"] == IntentType.KNOWLEDGE_SEARCH
    assert "Knowledge Base" in out_cust["final_response"]
    print(f"Graph Output (Customer Knowledge Search): {out_cust['final_response'][:80]}...")

    # Test Graph Execution for Customer Unauthorized Action
    state_unauth = {
        "user_id": "cust_123",
        "user_role": UserRole.CUSTOMER,
        "raw_message": "Run SQL database query on users table",
        "conversation_id": "test_conv_02",
        "execution_trace": []
    }
    out_unauth = enterprise_agent_graph.invoke(state_unauth)
    assert out_unauth["is_authorized"] is False
    assert "403 Forbidden" in out_unauth["final_response"]
    print(f"Graph Output (Customer RBAC Rejection): {out_unauth['final_response']}")

    # Test Graph Execution for Admin Authorized Action
    state_admin = {
        "user_id": "admin_boss",
        "user_role": UserRole.ADMIN,
        "raw_message": "Run SQL database query on users table",
        "conversation_id": "test_conv_03",
        "execution_trace": []
    }
    out_admin = enterprise_agent_graph.invoke(state_admin)
    assert out_admin["is_authorized"] is True
    assert "Admin Console" in out_admin["final_response"]
    print(f"Graph Output (Admin Database Query): {out_admin['final_response'][:80]}...")

    print("\n=======================================================")
    print("ALL PHASE 1 TESTS PASSED SUCCESSFULLY! (100% SUCCESS)")
    print("=======================================================")


if __name__ == "__main__":
    run_all_tests()
