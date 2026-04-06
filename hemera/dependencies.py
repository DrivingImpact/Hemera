"""FastAPI dependencies for authentication and authorization."""

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from hemera.services.clerk import verify_clerk_token, ClerkUser

_bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    token: str = None,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
) -> ClerkUser:
    cred_token = credentials.credentials if hasattr(credentials, "credentials") else ""
    raw_token = token or cred_token
    if not raw_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = verify_clerk_token(raw_token)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user


def require_admin(current_user: ClerkUser = Depends(get_current_user)) -> ClerkUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
