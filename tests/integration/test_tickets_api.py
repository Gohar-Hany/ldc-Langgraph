import pytest
from unittest.mock import patch
from app.schemas.ticket_schema import TicketResponse, TicketStatus, TicketPriority, TicketCategory


def test_customer_cannot_view_all_tickets(client, customer_token):
    """RBAC test: Customers must receive 403 Forbidden when accessing the enterprise queue."""
    response = client.get(
        "/api/v1/tickets",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 403
    error_msg = response.json().get("error", {}).get("message", "") or response.json().get("detail", "")
    assert "Customers are not authorized" in error_msg


def test_support_agent_can_view_all_tickets(client, support_agent_token):
    """RBAC test: Support Agents are authorized to inspect the enterprise ticket queue."""
    mock_ticket = TicketResponse(
        id=1,
        title="Sample issue",
        description="Sample desc",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category=TicketCategory.GENERAL,
        created_by="user_01"
    )
    with patch("app.services.database_service.database_service.list_all_tickets", return_value=[mock_ticket]):
        response = client.get(
            "/api/v1/tickets",
            headers={"Authorization": f"Bearer {support_agent_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1
        assert response.json()[0]["id"] == 1


def test_customer_can_view_my_tickets(client, customer_token):
    """Customers can view their own isolated tickets via /tickets/my."""
    mock_ticket = TicketResponse(
        id=99,
        title="My private issue",
        description="Private ticket details",
        status=TicketStatus.OPEN,
        priority=TicketPriority.LOW,
        category=TicketCategory.SOFTWARE,
        created_by="test_customer"
    )
    with patch("app.services.database_service.database_service.get_user_tickets", return_value=[mock_ticket]):
        response = client.get(
            "/api/v1/tickets/my",
            headers={"Authorization": f"Bearer {customer_token}"}
        )
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["created_by"] == "test_customer"


def test_customer_cannot_update_ticket(client, customer_token):
    """RBAC test: Customers cannot patch ticket status or assignees."""
    response = client.patch(
        "/api/v1/tickets/1",
        json={"status": "resolved"},
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert response.status_code == 403


def test_agent_can_create_ticket(client, support_agent_token):
    """Agents can create tickets on behalf of users."""
    mock_ticket = TicketResponse(
        id=105,
        title="Created by Agent",
        description="Printer offline on 4th floor",
        status=TicketStatus.OPEN,
        priority=TicketPriority.HIGH,
        category=TicketCategory.HARDWARE,
        created_by="test_support_agent"
    )
    with patch("app.services.database_service.database_service.create_ticket", return_value=mock_ticket):
        response = client.post(
            "/api/v1/tickets",
            json={
                "title": "Created by Agent",
                "description": "Printer offline on 4th floor",
                "priority": "high",
                "category": "hardware"
            },
            headers={"Authorization": f"Bearer {support_agent_token}"}
        )
        assert response.status_code == 201
        assert response.json()["id"] == 105
