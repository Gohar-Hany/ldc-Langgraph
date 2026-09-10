from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.auth_schema import UserProfile, UserRole
from app.schemas.ticket_schema import (
    TicketCreate,
    TicketUpdate,
    TicketResponse,
    TicketFilter,
    TicketStatus,
    TicketPriority,
    TicketCategory
)
from app.api.dependencies import get_current_user
from app.services.database_service import database_service
from app.core.logging import logger

router = APIRouter(prefix="/tickets", tags=["Ticket Management (Phase 3)"])


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket"
)
async def create_ticket(
    body: TicketCreate,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Creates a new support ticket in Supabase.
    Accessible to all authenticated roles (Customer, Support Agent, Senior Agent, Admin).
    """
    logger.info(f"[API: /tickets] Creating ticket for user '{current_user.id}' ({current_user.role.value}): '{body.title}'")
    try:
        new_ticket = database_service.create_ticket(user_id=current_user.id, data=body)
        database_service.log_audit(
            user_id=current_user.id,
            action="api_create_ticket",
            details={"ticket_id": new_ticket.id, "title": new_ticket.title}
        )
        return new_ticket
    except Exception as e:
        logger.error(f"[API: /tickets: Error] Failed to create ticket: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create ticket: {str(e)}"
        )


@router.get(
    "/my",
    response_model=List[TicketResponse],
    summary="Get tickets for currently authenticated user"
)
async def get_my_tickets(
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Retrieves all support tickets created by the current authenticated user.
    Provides strict Customer Data Isolation.
    """
    logger.info(f"[API: /tickets/my] Fetching tickets for user '{current_user.id}'")
    return database_service.get_user_tickets(current_user.id)


@router.get(
    "",
    response_model=List[TicketResponse],
    summary="List all tickets (Agent & Admin only)"
)
async def list_tickets(
    ticket_status: Optional[TicketStatus] = Query(None, alias="status", description="Filter by status"),
    priority: Optional[TicketPriority] = Query(None, description="Filter by priority"),
    category: Optional[TicketCategory] = Query(None, description="Filter by category"),
    created_by: Optional[str] = Query(None, description="Filter by author user_id"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Lists support tickets with optional filtering.
    RBAC Enforcement:
    - Customer role receives 403 Forbidden.
    - Support Agent, Senior Agent, and Admin can view all tickets.
    """
    if current_user.role == UserRole.CUSTOMER:
        logger.warning(f"[API: /tickets] Forbidden access attempt by customer '{current_user.id}'")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers are not authorized to view the enterprise ticket queue. Use /tickets/my instead."
        )

    filters = TicketFilter(
        status=ticket_status,
        priority=priority,
        category=category,
        created_by=created_by,
        limit=limit,
        offset=offset
    )
    return database_service.list_all_tickets(
        filters=filters,
        actor_role=current_user.role.value,
        actor_id=current_user.id
    )


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update ticket status, priority, or assignee (Agent & Admin only)"
)
async def update_ticket(
    ticket_id: int,
    body: TicketUpdate,
    current_user: UserProfile = Depends(get_current_user)
):
    """
    Updates ticket status, priority, or assignee in Supabase.
    RBAC Enforcement:
    - Customer role receives 403 Forbidden.
    - Support Agent, Senior Agent, Admin allowed.
    """
    if current_user.role == UserRole.CUSTOMER:
        logger.warning(f"[API: /tickets/{ticket_id}] Customer '{current_user.id}' attempted modification.")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Customers are not authorized to modify ticket lifecycle status or assignees."
        )

    updated = database_service.update_ticket(
        ticket_id=ticket_id,
        data=body,
        actor_role=current_user.role.value
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ticket #{ticket_id} not found."
        )

    database_service.log_audit(
        user_id=current_user.id,
        action="api_update_ticket",
        details={"ticket_id": ticket_id, "updates": body.model_dump(exclude_unset=True)}
    )
    return updated
