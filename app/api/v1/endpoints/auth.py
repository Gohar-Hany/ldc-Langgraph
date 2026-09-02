from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.security import create_access_token
from app.schemas.auth_schema import Token, UserProfile, UserRole
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenRequest(BaseModel):
    user_id: str = Field(default="user_01", json_schema_extra={"example": "user_01"})
    role: UserRole = Field(default=UserRole.CUSTOMER, json_schema_extra={"example": UserRole.CUSTOMER})


@router.post("/token", response_model=Token, summary="Generate a test JWT token for a specific role")
async def generate_role_token(body: TokenRequest):
    """
    Generates a signed JWT Bearer token with the requested role.
    Used for testing Role-Based Access Control (RBAC) across:
    - customer
    - support_agent
    - senior_agent
    - admin
    """
    token_str = create_access_token(
        subject=body.user_id,
        role=body.role.value,
        additional_claims={"name": body.user_id.capitalize()}
    )
    return Token(
        access_token=token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        role=body.role
    )


@router.get("/me", response_model=UserProfile, summary="Get current authenticated user profile")
async def get_my_profile(current_user: UserProfile = Depends(get_current_user)):
    return current_user
