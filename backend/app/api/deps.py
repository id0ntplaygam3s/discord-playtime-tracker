from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.permissions import PermissionCode
from app.core.config import get_settings
from app.core.security import decode_access_token_payload
from app.db.session import get_db
from app.models import AccountStatus, AdminUser, Role, User, UserAccount
from app.services.authz_service import resolve_permission

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@dataclass
class AuthUser:
    id: int | None
    username: str
    role: Role
    role_name: str
    is_active: bool = True
    is_guest: bool = False
    is_legacy_admin: bool = False
    account_id: int | None = None
    discord_user_id: int | None = None
    tracked_user_id: int | None = None
    role_id: int | None = None
    admin_user_id: int | None = None


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> AuthUser:
    settings = get_settings()
    payload = decode_access_token_payload(token, settings.secret_key)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    subject = str(payload.get("sub") or "")
    token_role = str(payload.get("role") or "")
    if payload.get("guest") is True or (subject == "guest" and token_role == Role.viewer.value):
        return AuthUser(id=None, username="guest", role=Role.viewer, role_name="guest", is_guest=True)

    principal_type = str(payload.get("typ") or "legacy_admin")

    if principal_type == "account":
        account_id = int(payload.get("aid") or 0)
        tracked_user_id = int(payload.get("uid") or 0)
        account = (
            db.query(UserAccount, User)
            .join(User, User.id == UserAccount.user_id)
            .filter(UserAccount.id == account_id, User.id == tracked_user_id)
            .first()
        )
        if not account:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
        account_row, tracked_user = account
        if account_row.role is None:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Account role not configured")
        if account_row.status != AccountStatus.active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Account is {account_row.status.value}")
        return AuthUser(
            id=account_row.id,
            username=tracked_user.username,
            role=Role.admin if account_row.role.name.value == "admin" else Role.viewer,
            role_name=account_row.role.name.value,
            is_active=True,
            is_guest=False,
            account_id=account_row.id,
            discord_user_id=tracked_user.discord_user_id,
            tracked_user_id=tracked_user.id,
            role_id=account_row.role_id,
            admin_user_id=None,
        )

    user = db.query(AdminUser).filter(AdminUser.username == subject, AdminUser.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return AuthUser(
        id=user.id,
        username=user.username,
        role=user.role,
        role_name="admin",
        is_active=user.is_active,
        is_guest=False,
        is_legacy_admin=True,
        admin_user_id=user.id,
    )


def require_admin(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if user.is_legacy_admin:
        return user
    if user.role_name != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return user


def require_permission(permission_code: str):
    def dependency(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> AuthUser:
        if not resolve_permission(
            db,
            permission_code,
            is_guest=user.is_guest,
            is_legacy_admin=user.is_legacy_admin,
            account_id=user.account_id,
            role_id=user.role_id,
        ):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission_code}")
        return user

    return dependency


def require_dashboard_view(user: AuthUser = Depends(require_permission(PermissionCode.DASHBOARD_VIEW))) -> AuthUser:
    return user


def audit_actor_fields(user: AuthUser) -> dict:
    if user.is_legacy_admin:
        return {
            "admin_user_id": user.admin_user_id,
            "actor_account_id": None,
            "actor_type": "legacy_admin",
            "actor_label": user.username,
        }
    if user.account_id is not None:
        label = user.username
        if user.role_name:
            label = f"{label} ({user.role_name})"
        return {
            "admin_user_id": None,
            "actor_account_id": user.account_id,
            "actor_type": "account",
            "actor_label": label,
        }
    return {
        "admin_user_id": None,
        "actor_account_id": None,
        "actor_type": "unknown",
        "actor_label": user.username,
    }
