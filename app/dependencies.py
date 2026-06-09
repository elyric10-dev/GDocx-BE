from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.auth import UserResponse
from app.services.supabase_client import get_supabase
from app.services.supabase_errors import handle_supabase_error
from app.services.supabase_retry import execute_supabase

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> UserResponse:
    token = credentials.credentials
    supabase = get_supabase()

    try:
        response = execute_supabase(lambda: supabase.auth.get_user(token))
    except Exception as exc:
        try:
            handle_supabase_error(exc)
        except HTTPException as http_exc:
            if http_exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service temporarily unavailable. Please retry.",
                ) from exc
            raise
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user = response.user
    if not user or not user.email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    return UserResponse(id=user.id, email=user.email)
