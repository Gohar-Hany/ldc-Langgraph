import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
from app.schemas.auth_schema import UserRole


def test_live_scenarios():
    client = TestClient(app)
    
    scenarios = [
        {
            "title": "Scenario 1: Customer queries corporate VPN setup guidelines",
            "role": UserRole.CUSTOMER,
            "user_id": "alice_customer",
            "message": "How to configure corporate VPN on MacOS?"
        },
        {
            "title": "Scenario 2: Customer attempts SQL Database query (Expected: 403 Forbidden)",
            "role": UserRole.CUSTOMER,
            "user_id": "alice_customer",
            "message": "Run SQL database query on users table"
        },
        {
            "title": "Scenario 3: Support Agent creates a new support ticket",
            "role": UserRole.SUPPORT_AGENT,
            "user_id": "bob_support",
            "message": "Create a new support ticket for email outage"
        },
        {
            "title": "Scenario 4: Support Agent attempts sensitive password reset (Expected: 403 Forbidden)",
            "role": UserRole.SUPPORT_AGENT,
            "user_id": "bob_support",
            "message": "Reset password for user John"
        },
        {
            "title": "Scenario 5: Senior Agent performs sensitive password reset (Authorized)",
            "role": UserRole.SENIOR_AGENT,
            "user_id": "charlie_senior",
            "message": "Reset password for user John"
        },
        {
            "title": "Scenario 6: Admin runs database health check query (Authorized)",
            "role": UserRole.ADMIN,
            "user_id": "david_admin",
            "message": "Run SQL database query on users table"
        }
    ]

    print("======================================================================")
    print("Live Demo Execution: 6 Role-Based Scenarios on FastAPI & LangGraph")
    print("======================================================================\n")

    for idx, sc in enumerate(scenarios, 1):
        token = create_access_token(subject=sc["user_id"], role=sc["role"].value)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.post(
            "/api/v1/chat",
            json={"message": sc["message"]},
            headers=headers
        )
        
        data = response.json()
        print(f"[{idx}] {sc['title']}")
        print(f"User: {sc['user_id']} | Role: {sc['role'].value}")
        print(f"Input Message: '{sc['message']}'")
        print(f"Detected Intent: {data['intent']} (Confidence: {data['confidence'] * 100:.0f}%)")
        print(f"Authorization: {data['is_authorized']}")
        print(f"Agent Final Response:\n{data['response']}")
        print("Execution Trace:")
        for step in data.get("execution_trace", []):
            print(f"  -> [{step['step_name']}] ({step['status']})")
        print("-" * 70 + "\n")


if __name__ == "__main__":
    test_live_scenarios()
