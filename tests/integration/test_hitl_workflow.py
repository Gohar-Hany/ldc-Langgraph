import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_hitl_sensitive_operation_pauses_on_interrupt(senior_agent_token):
    thread_id = "test_hitl_thread_interrupt_01"
    response = client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {senior_agent_token}"},
        json={
            "message": "Emergency: reboot core firewall and rotate admin passwords",
            "thread_id": thread_id
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert data["intent"] == "sensitive_operation"
    assert data["is_authorized"] is True
    assert data["approval_required"] is True
    assert data["approval_status"] == "PENDING"
    assert "APPROVAL REQUIRED" in data["response"]
    assert data["approval_details"] is not None


def test_hitl_check_pending_approval_status(admin_token, senior_agent_token):
    thread_id = "test_hitl_thread_status_01"
    # 1. Trigger interrupt
    client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {senior_agent_token}"},
        json={
            "message": "Elevate user_01 privileges to domain administrator",
            "thread_id": thread_id
        }
    )

    # 2. Check pending status
    status_resp = client.get(
        f"/api/v1/chat/approvals/{thread_id}/status",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["thread_id"] == thread_id
    assert status_data["is_pending_approval"] is True


def test_hitl_supervisor_approval_resumes_and_succeeds(admin_token, senior_agent_token):
    thread_id = "test_hitl_thread_approve_01"
    # 1. Trigger interrupt
    client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {senior_agent_token}"},
        json={
            "message": "Reboot database cluster node 02 for scheduled maintenance",
            "thread_id": thread_id
        }
    )

    # 2. Supervisor approves
    decide_resp = client.post(
        f"/api/v1/chat/approvals/{thread_id}/decide",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "approved": True,
            "reviewer_notes": "Approved by IT Infrastructure Director."
        }
    )
    assert decide_resp.status_code == 200
    decide_data = decide_resp.json()
    assert decide_data["approval_required"] is False
    assert decide_data["approval_status"] == "APPROVED"
    assert "Executed Successfully" in decide_data["response"]
    assert "Approved by IT Infrastructure Director" in decide_data["response"]


def test_hitl_supervisor_rejection_resumes_safely(admin_token, senior_agent_token):
    thread_id = "test_hitl_thread_reject_01"
    # 1. Trigger interrupt
    client.post(
        "/api/v1/chat",
        headers={"Authorization": f"Bearer {senior_agent_token}"},
        json={
            "message": "Reboot production server cluster and revoke all tokens",
            "thread_id": thread_id
        }
    )

    # 2. Supervisor rejects
    decide_resp = client.post(
        f"/api/v1/chat/approvals/{thread_id}/decide",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "approved": False,
            "reviewer_notes": "Declined: Unauthorized maintenance window."
        }
    )
    assert decide_resp.status_code == 200
    decide_data = decide_resp.json()
    assert decide_data["approval_required"] is False
    assert decide_data["approval_status"] == "REJECTED"
    assert "Rejected by Supervisor" in decide_data["response"]
    assert "Declined: Unauthorized maintenance window" in decide_data["response"]


def test_hitl_customer_role_forbidden_from_deciding(customer_token):
    thread_id = "test_hitl_thread_rbac_01"
    decide_resp = client.post(
        f"/api/v1/chat/approvals/{thread_id}/decide",
        headers={"Authorization": f"Bearer {customer_token}"},
        json={
            "approved": True,
            "reviewer_notes": "Attempting unauthorized approval"
        }
    )
    assert decide_resp.status_code == 403
    json_data = decide_resp.json()
    assert "Forbidden" in json_data["error"]["message"]
