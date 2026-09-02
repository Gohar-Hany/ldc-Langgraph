from fastapi.testclient import TestClient
from app.schemas.auth_schema import UserRole
from app.schemas.intent_schema import IntentType


def test_health_check_endpoint(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "app_name" in data


def test_generate_auth_token_endpoint(client: TestClient):
    response = client.post(
        "/api/v1/auth/token",
        json={"user_id": "test_agent", "role": UserRole.SUPPORT_AGENT.value}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == UserRole.SUPPORT_AGENT.value


def test_chat_greeting_as_guest(client: TestClient):
    response = client.post(
        "/api/v1/chat",
        json={"message": "Hello, good morning!"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentType.GREETING.value
    assert data["is_authorized"] is True
    assert "Enterprise IT Support" in data["response"]


def test_chat_rbac_customer_forbidden_database(client: TestClient, customer_token: str):
    headers = {"Authorization": f"Bearer {customer_token}"}
    response = client.post(
        "/api/v1/chat",
        json={"message": "Run SQL database query on users table"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentType.DATABASE_QUERY_OPERATION.value
    assert data["is_authorized"] is False
    assert "403 Forbidden" in data["response"]


def test_chat_rbac_admin_allowed_database(client: TestClient, admin_token: str):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = client.post(
        "/api/v1/chat",
        json={"message": "Run SQL database query on users table"},
        headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == IntentType.DATABASE_QUERY_OPERATION.value
    assert data["is_authorized"] is True
    assert "Admin Console" in data["response"]
