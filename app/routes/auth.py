from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import get_current_user
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from app.services.supabase_client import get_supabase, get_supabase_admin

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterRequest) -> AuthResponse:
    supabase = get_supabase()

    try:
        response = supabase.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    session = response.session
    user = response.user

    if not session or not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Check your email for confirmation if required.",
        )

    if body.full_name:
        try:
            admin = get_supabase_admin()
            admin.table("profiles").update({"full_name": body.full_name}).eq("id", user.id).execute()
        except Exception:
            pass

    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user_id=user.id,
        email=user.email or body.email,
    )


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest) -> AuthResponse:
    supabase = get_supabase()

    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        ) from exc

    session = response.session
    user = response.user

    if not session or not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return AuthResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user_id=user.id,
        email=user.email or body.email,
    )


@router.post("/logout")
def logout() -> dict[str, str]:
    supabase = get_supabase()
    supabase.auth.sign_out()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
def me(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
    return current_user
