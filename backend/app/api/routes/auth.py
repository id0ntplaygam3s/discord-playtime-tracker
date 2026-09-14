from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models import AdminUser, Role
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(AdminUser).filter(AdminUser.username == payload.username, AdminUser.is_active.is_(True)).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    settings = get_settings()
    token = create_access_token(
        user.username,
        settings.secret_key,
        settings.access_token_expire_minutes,
        extra_claims={"role": user.role.value},
    )
    return TokenResponse(access_token=token)


@router.post("/guest", response_model=TokenResponse)
def guest_login() -> TokenResponse:
    settings = get_settings()
    token = create_access_token(
        "guest",
        settings.secret_key,
        settings.access_token_expire_minutes,
        extra_claims={"role": Role.viewer.value, "guest": True},
    )
    return TokenResponse(access_token=token)


@router.get("/me")
def me(user: AuthUser = Depends(get_current_user)) -> dict:
    return {"username": user.username, "role": user.role.value}
