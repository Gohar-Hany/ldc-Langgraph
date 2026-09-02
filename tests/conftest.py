import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.schemas.auth_schema import UserRole


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def customer_token():
    return create_access_token(
        subject="test_customer",
        role=UserRole.CUSTOMER.value,
        additional_claims={"name": "Alice Customer"}
    )


@pytest.fixture
def support_agent_token():
    return create_access_token(
        subject="test_support_agent",
        role=UserRole.SUPPORT_AGENT.value,
        additional_claims={"name": "Bob Support"}
    )


@pytest.fixture
def senior_agent_token():
    return create_access_token(
        subject="test_senior_agent",
        role=UserRole.SENIOR_AGENT.value,
        additional_claims={"name": "Charlie Senior"}
    )


@pytest.fixture
def admin_token():
    return create_access_token(
        subject="test_admin",
        role=UserRole.ADMIN.value,
        additional_claims={"name": "David Admin"}
    )
