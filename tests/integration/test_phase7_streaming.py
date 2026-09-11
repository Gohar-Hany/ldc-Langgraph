import json
import pytest
from fastapi.testclient import TestClient
from app.main import create_application

app = create_application()
client = TestClient(app)

bypass_headers = {"X-Bypass-Rate-Limit": "true"}


def parse_sse_events(raw_text: str):
    """
    Parses a raw Server-Sent Events (SSE) text stream into a structured list of dictionaries:
    [{'event': 'step', 'data': {...}}, ...]
    """
    events = []
    current_event = "message"
    current_data = []

    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            if current_data:
                combined_data = "\n".join(current_data)
                try:
                    parsed_json = json.loads(combined_data)
                except Exception:
                    parsed_json = combined_data
                events.append({"event": current_event, "data": parsed_json})
                current_data = []
                current_event = "message"
            continue

        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data.append(line[len("data:"):].strip())

    if current_data:
        combined_data = "\n".join(current_data)
        try:
            parsed_json = json.loads(combined_data)
        except Exception:
            parsed_json = combined_data
        events.append({"event": current_event, "data": parsed_json})

    return events


def test_stream_endpoint_invalid_token_returns_401():
    """Invalid token must be rejected with HTTP 401."""
    resp = client.post(
        "/api/v1/chat/stream",
        headers={"Authorization": "Bearer invalid_malformed_token_abc"},
        json={"message": "Hello with bad token"}
    )
    assert resp.status_code == 401


def test_stream_endpoint_unauthenticated_guest_allowed(customer_token):
    """Unauthenticated requests default to anonymous-guest with customer permissions."""
    resp = client.post(
        "/api/v1/chat/stream",
        headers=bypass_headers,
        json={"message": "Hello support!", "thread_id": "stream_guest_01"}
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


def test_stream_greeting_emits_valid_sse_events(customer_token):
    """
    Verifies that greeting requests stream well-formed SSE chunks:
    step, thought, token, and done events.
    """
    resp = client.post(
        "/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {customer_token}", **bypass_headers},
        json={"message": "Hello support team!", "thread_id": "stream_test_greet_01"}
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = parse_sse_events(resp.text)
    assert len(events) >= 4

    event_types = [e["event"] for e in events]
    assert "step" in event_types
    assert "thought" in event_types
    assert "token" in event_types
    assert "done" in event_types

    # Validate done payload structure
    done_event = next(e for e in events if e["event"] == "done")
    done_data = done_event["data"]
    assert "final_response" in done_data
    assert "intent" in done_data
    assert done_data["is_authorized"] is True
    assert "Hello" in done_data["final_response"] or "مرحبا" in done_data["final_response"]


def test_stream_customer_rbac_denial_emits_unauthorized_event(customer_token):
    """
    Verifies that unauthorized actions stream handle_unauthorized node
    and conclude with a 403 Forbidden explanation.
    """
    resp = client.post(
        "/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {customer_token}", **bypass_headers},
        json={"message": "Run SQL query SELECT * FROM users;", "thread_id": "stream_test_rbac_01"}
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = parse_sse_events(resp.text)
    done_event = next(e for e in events if e["event"] == "done")
    done_data = done_event["data"]

    assert done_data["is_authorized"] is False
    assert "403" in done_data["final_response"]


def test_stream_hitl_interrupt_emits_interrupt_event(admin_token):
    """
    Verifies that high-privilege sensitive operations trigger an
    'interrupt' SSE event and halt cleanly.
    """
    thread_id = "stream_test_hitl_01"
    resp = client.post(
        "/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {admin_token}", **bypass_headers},
        json={"message": "Reset user password for john.smith", "thread_id": thread_id}
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]

    assert "interrupt" in event_types
    interrupt_event = next(e for e in events if e["event"] == "interrupt")
    assert interrupt_event["data"]["approval_required"] is True
    assert interrupt_event["data"]["status"] == "PENDING_SUPERVISOR_APPROVAL"
    assert interrupt_event["data"]["thread_id"] == thread_id


def test_stream_knowledge_search_rag_pipeline(customer_token):
    """
    Verifies that knowledge search executes the RAG pipeline steps
    and finishes with grounded sources in the done event.
    """
    resp = client.post(
        "/api/v1/chat/stream",
        headers={"Authorization": f"Bearer {customer_token}", **bypass_headers},
        json={"message": "How do I configure VPN on my laptop?", "thread_id": "stream_test_rag_01"}
    )
    assert resp.status_code == 200
    events = parse_sse_events(resp.text)

    event_types = [e["event"] for e in events]
    assert "token" in event_types
    assert "done" in event_types

    done_event = next(e for e in events if e["event"] == "done")
    assert done_event["data"]["intent"] == "knowledge_search"
    assert done_event["data"]["is_authorized"] is True
