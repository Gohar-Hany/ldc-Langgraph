import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def customer_headers():
    token = create_access_token(subject="alice_customer", role="customer")
    return {"Authorization": f"Bearer {token}"}


def test_rag_vpn_query_returns_grounded_answer(client, customer_headers):
    payload = {
        "message": "How do I configure GlobalProtect VPN on MacOS?",
        "thread_id": "test_rag_macos_vpn"
    }
    response = client.post("/api/v1/chat", json=payload, headers=customer_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["intent"] == "knowledge_search"
    assert data["is_authorized"] is True
    assert data["thread_id"] == "test_rag_macos_vpn"
    assert len(data["sources"]) > 0
    assert any("vpn_access_policy.md" in src for src in data["sources"])
    
    # Check execution trace
    step_names = [s["step_name"] for s in data["execution_trace"]]
    assert "receive_message" in step_names
    assert "intent_classification" in step_names
    assert "rag_retrieve" in step_names
    assert "rag_grade" in step_names
    assert "rag_generate" in step_names



def test_rag_wifi_query_returns_sources(client, customer_headers):
    payload = {
        "message": "What are the security requirements to connect to Corp-Secure Wi-Fi?",
        "thread_id": "test_rag_wifi_01"
    }
    response = client.post("/api/v1/chat", json=payload, headers=customer_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["intent"] == "knowledge_search"
    assert len(data["sources"]) > 0
    assert any("wifi_network_access.md" in src for src in data["sources"])


def test_thread_id_persistence_preservation(client, customer_headers):
    custom_thread = "custom_session_thread_12345"
    payload = {
        "message": "What is the password expiration policy for employees?",
        "thread_id": custom_thread
    }
    response = client.post("/api/v1/chat", json=payload, headers=customer_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert data["thread_id"] == custom_thread
    assert data["conversation_id"] == custom_thread
