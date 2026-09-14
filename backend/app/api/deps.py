from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token_payload
from app.db.session import get_db
from app.models import AdminUser, Role

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class AuthUser:
    id: int | None
    username: str
    role: Role
    is_active: bool = True
    is_guest: bool = False


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> AuthUser:
    settings = get_settings()
    payload = decode_access_token_payload(token, settings.secret_key)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    subject = str(payload.get("sub") or "")
    token_role = str(payload.get("role") or "")
    if payload.get("guest") is True or (subject == "guest" and token_role == Role.viewer.value):
        return AuthUser(id=None, username="guest", role=Role.viewer, is_guest=True)

    user = db.query(AdminUser).filter(AdminUser.username == subject, AdminUser.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return AuthUser(id=user.id, username=user.username, role=user.role, is_active=user.is_active, is_guest=False)


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.role != Role.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user
