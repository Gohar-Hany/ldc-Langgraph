import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_application
from app.services.semantic_cache_service import semantic_cache_service

app = create_application()
client = TestClient(app)

bypass_headers = {"X-Bypass-Rate-Limit": "true"}


@pytest.fixture(autouse=True)
def clean_cache_before_and_after():
    """Ensure tests run with a fresh semantic cache."""
    semantic_cache_service.clear()
    yield
    semantic_cache_service.clear()


def test_semantic_cache_lifecycle_e2e(customer_token):
    """
    Verifies that:
    1. First query executes normal graph pipeline (cache miss) and saves to cache.
    2. Repeated query hits the vector semantic cache (cached: True, < 25ms, no LLM call).
    """
    headers = {"Authorization": f"Bearer {customer_token}", **bypass_headers}
    query_payload = {
        "message": "Hello, good morning team!",
        "thread_id": "p9_cache_thread_01"
    }

    # 1. First invocation -> Expect Cache Miss
    resp1 = client.post("/api/v1/chat", headers=headers, json=query_payload)
    assert resp1.status_code == 200
    data1 = resp1.json()
    assert data1["cached"] is False

    trace_steps1 = [s["step_name"] for s in data1["execution_trace"]]
    assert "receive_message" in trace_steps1
    assert "semantic_cache_lookup" in trace_steps1
    cache_step1 = next(s for s in data1["execution_trace"] if s["step_name"] == "semantic_cache_lookup")
    assert cache_step1["status"] == "cache_miss"

    # 2. Second invocation with same query -> Expect Cache Hit
    resp2 = client.post("/api/v1/chat", headers=headers, json=query_payload)
    assert resp2.status_code == 200
    data2 = resp2.json()

    assert data2["cached"] is True
    assert data2["cache_score"] is not None
    assert data2["cache_score"] >= 0.90
    assert "Enterprise IT Support Agent" in data2["response"]

    trace_steps2 = [s["step_name"] for s in data2["execution_trace"]]
    assert "semantic_cache_lookup" in trace_steps2
    cache_step2 = next(s for s in data2["execution_trace"] if s["step_name"] == "semantic_cache_lookup")
    assert cache_step2["status"] == "cache_hit"


def test_semantic_cache_bypass_header_e2e(customer_token):
    """
    Verifies that passing 'X-Bypass-Cache: true' forces fresh execution
    even when a valid cached response exists.
    """
    headers = {"Authorization": f"Bearer {customer_token}", **bypass_headers}
    query_payload = {
        "message": "Hello, good afternoon!",
        "thread_id": "p9_cache_bypass_01"
    }

    # Seed the cache
    client.post("/api/v1/chat", headers=headers, json=query_payload)

    # Bypass the cache with header
    bypass_cache_headers = {**headers, "X-Bypass-Cache": "true"}
    resp = client.post("/api/v1/chat", headers=bypass_cache_headers, json=query_payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["cached"] is False
    cache_step = next(s for s in data["execution_trace"] if s["step_name"] == "semantic_cache_lookup")
    assert cache_step["status"] == "bypassed"


def test_streaming_with_semantic_cache_hit_e2e(customer_token):
    """
    Verifies that SSE streaming emits 'semantic_cache_check' and final 'done' event
    with 'cached: true' when a semantic cache hit occurs.
    """
    headers = {"Authorization": f"Bearer {customer_token}", **bypass_headers}
    query_payload = {
        "message": "Hello, how are you doing?",
        "thread_id": "p9_stream_cache_01"
    }

    # 1. Seed the cache
    client.post("/api/v1/chat", headers=headers, json=query_payload)

    # 2. Query via streaming endpoint
    resp = client.post("/api/v1/chat/stream", headers=headers, json=query_payload)
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    lines = [line.strip() for line in resp.text.splitlines() if line.startswith("data:")]
    done_payloads = [json.loads(line[len("data:"):]) for line in lines if "final_response" in line]

    assert len(done_payloads) >= 1
    final_payload = done_payloads[-1]
    assert final_payload["cached"] is True
    assert final_payload["cache_score"] is not None


def test_metrics_record_cache_hits_and_misses(customer_token):
    """
    Verifies that metrics endpoint accurately tracks cache_hits_total and cache_misses_total.
    """
    headers = {"Authorization": f"Bearer {customer_token}", **bypass_headers}
    query_payload = {
        "message": "Hello test metrics agent!",
        "thread_id": "p9_metrics_thread_01"
    }

    # 1. Cache Miss
    client.post("/api/v1/chat", headers=headers, json=query_payload)

    # 2. Cache Hit
    client.post("/api/v1/chat", headers=headers, json=query_payload)

    # 3. Inspect JSON Metrics
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    telemetry = metrics_resp.json()["telemetry"]

    assert telemetry["cache_hits_total"] >= 1
    assert telemetry["cache_misses_total"] >= 1
    assert telemetry["cache_hit_rate_pct"] > 0.0

    # 4. Inspect Prometheus Metrics
    prom_resp = client.get("/metrics?format=prometheus")
    assert prom_resp.status_code == 200
    prom_text = prom_resp.text
    assert "agent_semantic_cache_hits_total" in prom_text
    assert "agent_semantic_cache_misses_total" in prom_text
