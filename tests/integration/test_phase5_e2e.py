import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from app.services.metrics_service import metrics_service

client = TestClient(app)


def test_correlation_id_injection_and_propagation():
    # Case 1: Automatic generation
    resp1 = client.get("/health")
    assert resp1.status_code == 200
    assert "X-Request-ID" in resp1.headers
    assert resp1.headers["X-Request-ID"].startswith("req_")
    assert "X-Process-Time-Ms" in resp1.headers
    assert float(resp1.headers["X-Process-Time-Ms"]) >= 0.0

    # Case 2: Client provided correlation ID
    custom_trace = "trace_soc_incident_9988"
    resp2 = client.get("/health", headers={"X-Request-ID": custom_trace})
    assert resp2.status_code == 200
    assert resp2.headers["X-Request-ID"] == custom_trace


def test_health_live_liveness_probe():
    resp = client.get("/health/live")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_health_ready_readiness_probe():
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ["ready", "partially_degraded"]
    deps = data["dependencies"]
    assert "supabase_postgresql" in deps
    assert "qdrant_vector_db" in deps
    assert "llm_orchestrator" in deps
    assert "tavily_external_search" in deps


def test_metrics_json_and_prometheus_exposition():
    # JSON format
    resp_json = client.get("/metrics?format=json")
    assert resp_json.status_code == 200
    data = resp_json.json()
    assert "telemetry" in data
    assert data["telemetry"]["total_requests"] >= 1
    assert "requests_by_status" in data["telemetry"]
    assert "requests_by_endpoint" in data["telemetry"]

    # Prometheus format
    resp_prom = client.get("/metrics?format=prometheus")
    assert resp_prom.status_code == 200
    text = resp_prom.text
    assert "# HELP http_requests_total" in text
    assert "# TYPE http_requests_total counter" in text
    assert "http_requests_total" in text


def test_rate_limiter_triggers_429_on_burst(customer_token):
    from app.api.middlewares.rate_limiter import RateLimiterMiddleware
    RateLimiterMiddleware.reset()

    original_limit = settings.RATE_LIMIT_PER_MINUTE
    original_enabled = settings.RATE_LIMIT_ENABLED
    try:
        settings.RATE_LIMIT_ENABLED = True
        settings.RATE_LIMIT_PER_MINUTE = 3  # Set tight threshold

        responses = []
        # Rapid fire 5 requests
        for i in range(5):
            r = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {customer_token}"}
            )
            responses.append(r.status_code)

        # First 3 should pass, subsequent should be 429
        assert 200 in responses[:3]
        assert 429 in responses[3:]
    finally:
        # Restore configuration
        settings.RATE_LIMIT_PER_MINUTE = original_limit
        settings.RATE_LIMIT_ENABLED = original_enabled


def test_e2e_multi_role_comprehensive_journey(
    customer_token,
    support_agent_token,
    senior_agent_token,
    admin_token
):
    """
    End-to-end integration test validating full multi-role RBAC,
    RAG, Tavily Search, Supabase Tickets, and HITL Lifecycle in one test session.
    """
    bypass_headers = {"X-Bypass-Rate-Limit": "true"}

    # 1. Customer: Knowledge search (RAG)
    cust_rag = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {customer_token}", **bypass_headers},
        json={"message": "How do I configure VPN?", "thread_id": "e2e_cust_01"}
    )
    assert cust_rag.status_code == 200
    assert cust_rag.json()["intent"] == "knowledge_search"
    assert cust_rag.json()["is_authorized"] is True

    # 2. Customer: Attempt direct SQL query -> 403 Forbidden
    cust_sql = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {customer_token}", **bypass_headers},
        json={"message": "Run SQL query SELECT * FROM users;", "thread_id": "e2e_cust_02"}
    )
    assert cust_sql.status_code == 200
    assert cust_sql.json()["is_authorized"] is False
    assert "403" in cust_sql.json()["response"]

    # 3. Support Agent: Create ticket via REST API
    from unittest.mock import patch
    from app.schemas.ticket_schema import TicketResponse, TicketStatus, TicketPriority, TicketCategory

    mock_ticket = TicketResponse(
        id=777,
        title="E2E Printer connectivity issue in Floor 3",
        description="Network printer dropping packets intermittently.",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category=TicketCategory.HARDWARE,
        created_by="test_support_agent"
    )
    with patch("app.services.database_service.database_service.create_ticket", return_value=mock_ticket):
        ticket_resp = client.post(
            "/api/v1/tickets",
            headers={"Authorization": f"Bearer {support_agent_token}", **bypass_headers},
            json={
                "title": "E2E Printer connectivity issue in Floor 3",
                "description": "Network printer dropping packets intermittently.",
                "priority": "medium",
                "category": "hardware"
            }
        )
        assert ticket_resp.status_code == 201
        assert ticket_resp.json()["id"] == 777

    # 4. Support Agent: Query external cloud status via Tavily
    agent_tavily = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {support_agent_token}", **bypass_headers},
        json={"message": "What is the status of GitHub and Cloudflare network?", "thread_id": "e2e_agent_01"}
    )
    assert agent_tavily.status_code == 200
    assert agent_tavily.json()["intent"] == "external_api_search"

    # 5. Senior Agent: Sensitive operation triggers HITL Interrupt
    thread_hitl = "e2e_hitl_lifecycle_01"
    senior_hitl = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {senior_agent_token}", **bypass_headers},
        json={
            "message": "Rotate root administrative credentials and restart core gateway",
            "thread_id": thread_hitl
        }
    )
    assert senior_hitl.status_code == 200
    assert senior_hitl.json()["approval_required"] is True
    assert senior_hitl.json()["approval_status"] == "PENDING"

    # 6. Admin: Approves sensitive operation -> Resumes execution
    admin_decide = client.post(
        f"/api/v1/chat/approvals/{thread_hitl}/decide",
        headers={"Authorization": f"Bearer {admin_token}", **bypass_headers},
        json={"approved": True, "reviewer_notes": "E2E verification approved by Admin"}
    )
    assert admin_decide.status_code == 200
    assert admin_decide.json()["approval_status"] == "APPROVED"
    assert "Executed Successfully" in admin_decide.json()["response"]
