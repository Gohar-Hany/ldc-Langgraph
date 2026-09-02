from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.security import decode_access_token
from app.schemas.auth_schema import UserProfile, UserRole

security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)
) -> UserProfile:
    """
    Extracts and validates the JWT Bearer token from the request.
    If no token is provided, returns a default Guest / Customer profile.
    """
    if not credentials:
        # Default unauthenticated access treated as Customer
        return UserProfile(
            id="anonymous-guest",
            email="guest@company.com",
            full_name="Guest User",
            role=UserRole.CUSTOMER
        )

    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub", "unknown")
    role_str = payload.get("role", UserRole.CUSTOMER.value)
    
    try:
        user_role = UserRole(role_str)
    except ValueError:
        user_role = UserRole.CUSTOMER

    return UserProfile(
        id=user_id,
        email=f"{user_id}@company.com",
        full_name=payload.get("name", user_id.capitalize()),
        role=user_role
    )


def require_role(*allowed_roles: UserRole):
    """
    FastAPI dependency guard enforcing specific role permissions.
    """
    def role_checker(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role: {current_user.role.value}"
            )
        return current_user
    return role_checker
