from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class UserRole(str, Enum):
    CUSTOMER = "customer"
    SUPPORT_AGENT = "support_agent"
    SENIOR_AGENT = "senior_agent"
    ADMIN = "admin"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: UserRole


class TokenPayload(BaseModel):
    sub: str = Field(..., description="User ID or Email")
    role: UserRole = Field(..., description="Assigned User Role")
    exp: Optional[int] = None
    iat: Optional[int] = None


class UserLogin(BaseModel):
    email: str = Field(..., json_schema_extra={"example": "agent@company.com"})
    password: str = Field(..., min_length=4)


class UserProfile(BaseModel):
    id: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool = True
