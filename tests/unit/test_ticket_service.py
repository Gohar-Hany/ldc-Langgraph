import pytest
from app.schemas.ticket_schema import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketStatus,
    TicketPriority,
    TicketCategory,
    TicketFilter
)
from app.schemas.auth_schema import UserRole


def test_ticket_create_validation():
    ticket = TicketCreate(
        title="VPN Connection failure",
        description="Cannot authenticate with WireGuard on Windows 11.",
        priority=TicketPriority.HIGH,
        category=TicketCategory.NETWORK
    )
    assert ticket.title == "VPN Connection failure"
    assert ticket.priority == TicketPriority.HIGH
    assert ticket.category == TicketCategory.NETWORK


def test_ticket_update_validation():
    update = TicketUpdate(
        status=TicketStatus.IN_PROGRESS,
        assigned_to="agent_01",
        resolution_notes="Investigating VPN gateway logs."
    )
    assert update.status == TicketStatus.IN_PROGRESS
    assert update.assigned_to == "agent_01"


def test_ticket_response_serialization():
    resp = TicketResponse(
        id=101,
        title="Laptop screen issue",
        description="Flickering screen on dock",
        status=TicketStatus.OPEN,
        priority=TicketPriority.MEDIUM,
        category=TicketCategory.HARDWARE,
        created_by="user_01"
    )
    assert resp.id == 101
    assert resp.status == TicketStatus.OPEN
    assert resp.created_by == "user_01"


def test_ticket_filter_defaults():
    filt = TicketFilter()
    assert filt.limit == 20
    assert filt.offset == 0
    assert filt.status is None
