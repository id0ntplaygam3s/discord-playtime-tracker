from datetime import datetime, timezone
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, audit_actor_fields, require_admin
from app.core.permissions import PermissionCode
from app.core.security import hash_password
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.models import (
    AccountStatus,
    AppRole,
    AppRoleName,
    AuditAction,
    Permission,
    RolePermission,
    User,
    UserAccount,
    UserPermissionOverride,
)
from app.services.authz_service import resolve_permission
from app.services.session_service import write_audit_log
from app.services.settings_service import get_all_settings, set_setting
from app.workers.demo_data import seed_demo_data

router = APIRouter(prefix="/admin", tags=["admin"])


def _account_guild_id(db: Session, account: UserAccount) -> int:
    if account.user is not None:
        return int(account.user.guild_id)
    row = db.query(User.guild_id).filter(User.id == account.user_id).first()
    if row is not None:
        return int(row[0])
    return resolve_guild_id(db, 0)


def _require_permission_or_admin(db: Session, user: AuthUser, permission_code: str) -> None:
    if user.is_legacy_admin:
        return
    allowed = resolve_permission(
        db,
        permission_code,
        is_guest=user.is_guest,
        is_legacy_admin=user.is_legacy_admin,
        account_id=user.account_id,
        role_id=user.role_id,
    )
    if not allowed:
        raise HTTPException(status_code=403, detail=f"Missing permission: {permission_code}")


def _prevent_last_admin_loss(db: Session, account: UserAccount, new_role_name: str | None = None, disable: bool = False) -> None:
    role_name = account.role.name.value
    will_be_admin = role_name == AppRoleName.admin.value
    if new_role_name is not None:
        will_be_admin = new_role_name == AppRoleName.admin.value
    if not will_be_admin and role_name != AppRoleName.admin.value:
        return

    if disable:
        admin_count = (
            db.query(UserAccount)
            .join(AppRole, AppRole.id == UserAccount.role_id)
            .filter(AppRole.name == AppRoleName.admin, UserAccount.status == AccountStatus.active)
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot disable the last active admin account")
        return

    if role_name == AppRoleName.admin.value and new_role_name != AppRoleName.admin.value:
        admin_count = (
            db.query(UserAccount)
            .join(AppRole, AppRole.id == UserAccount.role_id)
            .filter(AppRole.name == AppRoleName.admin, UserAccount.status == AccountStatus.active)
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot demote the last active admin account")


@router.post("/demo-data")
def generate_demo_data(
    guild_id: int = Query(default=0),
    days: int = Query(default=30, ge=1, le=365),
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    seed_demo_data(db, guild_id, days=days)
    return {"ok": True}


@router.get("/users")
def admin_list_users(
    guild_id: int = Query(default=0),
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.USERS_MANAGE)
    guild_id = resolve_guild_id(db, guild_id)
    rows = (
        db.query(User, UserAccount, AppRole)
        .outerjoin(UserAccount, UserAccount.user_id == User.id)
        .outerjoin(AppRole, AppRole.id == UserAccount.role_id)
        .filter(User.guild_id == guild_id)
        .order_by(User.display_name.asc())
        .all()
    )
    payload = []
    for tracked_user, account, role in rows:
        payload.append(
            {
                "user_id": tracked_user.id,
                "discord_user_id": tracked_user.discord_user_id,
                "username": tracked_user.username,
                "display_name": tracked_user.display_name,
                "account_id": account.id if account else None,
                "account_status": account.status.value if account else None,
                "role": role.name.value if role else None,
                "created_at": account.created_at if account else None,
                "last_login_at": account.last_login_at if account else None,
            }
        )
    return payload


@router.post("/users/{account_id}/role")
def admin_change_role(
    account_id: int,
    payload: dict,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.USERS_MANAGE)
    new_role = str(payload.get("role") or "").strip().lower()
    if new_role not in {"guest", "user", "admin"}:
        raise HTTPException(status_code=400, detail="Invalid role")

    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    _prevent_last_admin_loss(db, account, new_role_name=new_role)
    role = db.query(AppRole).filter(AppRole.name == AppRoleName(new_role)).first()
    if role is None:
        raise HTTPException(status_code=500, detail="Role not configured")

    account.role_id = role.id
    write_audit_log(
        db,
        guild_id=_account_guild_id(db, account),
        action=AuditAction.role_changed,
        **audit_actor_fields(user),
        target_user_id=account.user_id,
        target_game_id=None,
        change_seconds=None,
        reason=f"Role set to {new_role}",
        metadata_json={"account_id": account.id, "role": new_role},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.post("/users/{account_id}/status")
def admin_change_status(
    account_id: int,
    payload: dict,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.USERS_MANAGE)
    status_value = str(payload.get("status") or "").strip().lower()
    if status_value not in {"active", "locked", "disabled", "pending"}:
        raise HTTPException(status_code=400, detail="Invalid status")

    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    target_status = AccountStatus(status_value)
    if target_status == AccountStatus.disabled:
        _prevent_last_admin_loss(db, account, disable=True)

    account.status = target_status
    if target_status == AccountStatus.active:
        account.locked_until = None
        account.failed_login_attempts = 0
        account.disabled_at = None
        account.disabled_by_admin_user_id = None
    elif target_status == AccountStatus.locked:
        account.locked_until = datetime.now(timezone.utc) + timedelta(minutes=30)
    elif target_status == AccountStatus.disabled:
        account.disabled_at = datetime.now(timezone.utc)
        account.disabled_by_admin_user_id = user.admin_user_id

    write_audit_log(
        db,
        guild_id=_account_guild_id(db, account),
        action=AuditAction.user_account_changed,
        **audit_actor_fields(user),
        target_user_id=account.user_id,
        target_game_id=None,
        change_seconds=None,
        reason=f"Status set to {target_status.value}",
        metadata_json={"account_id": account.id, "status": target_status.value},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.post("/users/{account_id}/unlock")
def admin_unlock_account(
    account_id: int,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.ACCOUNTS_UNLOCK)
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.status = AccountStatus.active
    account.locked_until = None
    account.failed_login_attempts = 0
    write_audit_log(
        db,
        guild_id=_account_guild_id(db, account),
        action=AuditAction.account_unlocked,
        **audit_actor_fields(user),
        target_user_id=account.user_id,
        target_game_id=None,
        change_seconds=None,
        reason="Account unlocked",
        metadata_json={"account_id": account.id},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.post("/users/{account_id}/reset-password")
def admin_reset_password(
    account_id: int,
    payload: dict,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.ACCOUNTS_RESET_PASSWORD)
    password = str(payload.get("new_password") or "")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    account.password_hash = hash_password(password)
    account.failed_login_attempts = 0
    account.locked_until = None
    if account.status in {AccountStatus.locked, AccountStatus.pending}:
        account.status = AccountStatus.active
    write_audit_log(
        db,
        guild_id=_account_guild_id(db, account),
        action=AuditAction.user_account_changed,
        **audit_actor_fields(user),
        target_user_id=account.user_id,
        target_game_id=None,
        change_seconds=None,
        reason="Password reset by admin",
        metadata_json={"account_id": account.id},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.get("/permissions")
def list_permissions(user: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    _require_permission_or_admin(db, user, PermissionCode.PERMISSIONS_VIEW)
    permissions = db.query(Permission).order_by(Permission.code.asc()).all()
    roles = db.query(AppRole).order_by(AppRole.id.asc()).all()

    role_map: dict[str, dict[str, bool]] = {role.name.value: {} for role in roles}
    rows = db.query(RolePermission).all()
    role_lookup = {r.id: r.name.value for r in roles}
    perm_lookup = {p.id: p.code for p in permissions}
    for row in rows:
        role_name = role_lookup.get(row.role_id)
        perm_code = perm_lookup.get(row.permission_id)
        if role_name and perm_code:
            role_map[role_name][perm_code] = bool(row.is_allowed)

    return {
        "permissions": [{"code": p.code, "description": p.description} for p in permissions],
        "roles": [{"name": r.name.value, "display_name": r.display_name} for r in roles],
        "role_permissions": role_map,
    }


@router.post("/permissions/roles/{role_name}")
def update_role_permissions(
    role_name: str,
    payload: dict,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.PERMISSIONS_MANAGE)
    try:
        role_enum = AppRoleName(role_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid role") from exc

    role = db.query(AppRole).filter(AppRole.name == role_enum).first()
    if role is None:
        raise HTTPException(status_code=404, detail="Role not found")

    updates = payload.get("permissions") or {}
    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="permissions must be an object")

    permissions = db.query(Permission).all()
    code_to_perm = {p.code: p for p in permissions}
    for code, value in updates.items():
        perm = code_to_perm.get(str(code))
        if perm is None:
            continue
        row = db.query(RolePermission).filter(RolePermission.role_id == role.id, RolePermission.permission_id == perm.id).first()
        allowed = bool(value)
        if row is None:
            row = RolePermission(role_id=role.id, permission_id=perm.id, is_allowed=allowed)
            db.add(row)
        else:
            row.is_allowed = allowed
    write_audit_log(
        db,
        guild_id=resolve_guild_id(db, 0),
        action=AuditAction.permission_changed,
        **audit_actor_fields(user),
        target_user_id=None,
        target_game_id=None,
        change_seconds=None,
        reason=f"Role permission matrix updated for {role_name}",
        metadata_json={"role": role_name, "updated_permissions": list(updates.keys())},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.get("/permissions/users/{account_id}")
def list_user_permission_overrides(
    account_id: int,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.PERMISSIONS_VIEW)
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    rows = (
        db.query(UserPermissionOverride, Permission)
        .join(Permission, Permission.id == UserPermissionOverride.permission_id)
        .filter(UserPermissionOverride.account_id == account_id)
        .all()
    )
    return [{"permission": perm.code, "is_allowed": row.is_allowed} for row, perm in rows]


@router.post("/permissions/users/{account_id}")
def set_user_permission_override(
    account_id: int,
    payload: dict,
    user: AuthUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_permission_or_admin(db, user, PermissionCode.PERMISSIONS_MANAGE)
    account = db.query(UserAccount).filter(UserAccount.id == account_id).first()
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")

    permission_code = str(payload.get("permission") or "").strip()
    mode = str(payload.get("mode") or "").strip().lower()
    if mode not in {"inherit", "allow", "deny"}:
        raise HTTPException(status_code=400, detail="mode must be one of inherit, allow, deny")

    perm = db.query(Permission).filter(Permission.code == permission_code).first()
    if perm is None:
        raise HTTPException(status_code=404, detail="Permission not found")

    row = (
        db.query(UserPermissionOverride)
        .filter(UserPermissionOverride.account_id == account_id, UserPermissionOverride.permission_id == perm.id)
        .first()
    )
    if mode == "inherit":
        if row is not None:
            db.delete(row)
    else:
        allow = mode == "allow"
        if row is None:
            db.add(UserPermissionOverride(account_id=account_id, permission_id=perm.id, is_allowed=allow))
        else:
            row.is_allowed = allow

    write_audit_log(
        db,
        guild_id=_account_guild_id(db, account),
        action=AuditAction.permission_changed,
        **audit_actor_fields(user),
        target_user_id=account.user_id,
        target_game_id=None,
        change_seconds=None,
        reason=f"Permission override {mode} for {permission_code}",
        metadata_json={"account_id": account.id, "permission": permission_code, "mode": mode},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.get("/settings")
def list_settings(user: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    _require_permission_or_admin(db, user, PermissionCode.SETTINGS_VIEW)
    return get_all_settings(db)


@router.post("/settings")
def update_settings(payload: dict, user: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    _require_permission_or_admin(db, user, PermissionCode.SETTINGS_MANAGE)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    for key, value in payload.items():
        if key in {"discord_bot_token", "database_url", "secret_key", "admin_password"}:
            continue
        set_setting(db, str(key), value, updated_by_admin_user_id=user.admin_user_id)
    write_audit_log(
        db,
        guild_id=resolve_guild_id(db, 0),
        action=AuditAction.settings_changed,
        **audit_actor_fields(user),
        target_user_id=None,
        target_game_id=None,
        change_seconds=None,
        reason="Runtime settings updated",
        metadata_json={"keys": sorted([str(k) for k in payload.keys()])},
        commit=False,
    )
    db.commit()
    return {"ok": True}
