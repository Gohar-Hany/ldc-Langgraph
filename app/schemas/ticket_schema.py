from typing import Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketCategory(str, Enum):
    NETWORK = "network"
    HARDWARE = "hardware"
    SOFTWARE = "software"
    SECURITY = "security"
    GENERAL = "general"


class TicketCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200, description="Brief summary of the issue")
    description: str = Field(..., min_length=5, description="Detailed problem description")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM, description="Ticket urgency level")
    category: TicketCategory = Field(default=TicketCategory.GENERAL, description="Problem domain category")


class TicketUpdate(BaseModel):
    status: Optional[TicketStatus] = Field(default=None, description="New ticket lifecycle status")
    priority: Optional[TicketPriority] = Field(default=None, description="Updated priority")
    category: Optional[TicketCategory] = Field(default=None, description="Updated category")
    assigned_to: Optional[str] = Field(default=None, description="Support agent user_id")
    resolution_notes: Optional[str] = Field(default=None, description="Resolution or investigation summary")


class TicketResponse(BaseModel):
    id: int = Field(..., description="Unique ticket identifier")
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    category: TicketCategory
    created_by: str
    assigned_to: Optional[str] = None
    resolution_notes: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class TicketFilter(BaseModel):
    status: Optional[TicketStatus] = None
    priority: Optional[TicketPriority] = None
    category: Optional[TicketCategory] = None
    created_by: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
