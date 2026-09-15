from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.permissions import PERMISSIONS
from app.models import AppRole, AppRoleName, Permission, RolePermission, UserPermissionOverride


def ensure_roles_and_permissions(db: Session) -> None:
    role_map: dict[AppRoleName, AppRole] = {}
    for role_name, display in (
        (AppRoleName.guest, "Guest"),
        (AppRoleName.user, "User"),
        (AppRoleName.admin, "Admin"),
    ):
        role = db.query(AppRole).filter(AppRole.name == role_name).first()
        if role is None:
            role = AppRole(name=role_name, display_name=display)
            db.add(role)
            db.flush()
        role_map[role_name] = role

    permission_map: dict[str, Permission] = {}
    for code, description in PERMISSIONS.items():
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm is None:
            perm = Permission(code=code, description=description)
            db.add(perm)
            db.flush()
        permission_map[code] = perm

    guest_allowed = {"dashboard.view", "games.view", "playtime.view", "users.view"}
    user_allowed = guest_allowed | {"users.view", "playtime.manage_own"}
    admin_allowed = set(permission_map.keys())

    _sync_role_permissions(db, role_map[AppRoleName.guest].id, permission_map, guest_allowed)
    _sync_role_permissions(db, role_map[AppRoleName.user].id, permission_map, user_allowed)
    _sync_role_permissions(db, role_map[AppRoleName.admin].id, permission_map, admin_allowed)
    db.flush()


def _sync_role_permissions(db: Session, role_id: int, permission_map: dict[str, Permission], allowed_codes: set[str]) -> None:
    for code, perm in permission_map.items():
        row = db.query(RolePermission).filter(RolePermission.role_id == role_id, RolePermission.permission_id == perm.id).first()
        should_allow = code in allowed_codes
        if row is None:
            db.add(RolePermission(role_id=role_id, permission_id=perm.id, is_allowed=should_allow))
        elif row.is_allowed != should_allow:
            row.is_allowed = should_allow


def resolve_permission(
    db: Session,
    permission_code: str,
    *,
    is_guest: bool,
    is_legacy_admin: bool,
    account_id: int | None,
    role_id: int | None,
) -> bool:
    if is_legacy_admin:
        return True

    ensure_roles_and_permissions(db)

    if role_id is not None:
        role = db.query(AppRole).filter(AppRole.id == role_id).first()
        if role is not None and role.name == AppRoleName.admin:
            return True

    perm = db.query(Permission).filter(Permission.code == permission_code).first()
    if perm is None:
        return False

    if account_id is not None:
        override = (
            db.query(UserPermissionOverride)
            .filter(UserPermissionOverride.account_id == account_id, UserPermissionOverride.permission_id == perm.id)
            .first()
        )
        if override is not None:
            return bool(override.is_allowed)

    if role_id is not None:
        row = db.query(RolePermission).filter(RolePermission.role_id == role_id, RolePermission.permission_id == perm.id).first()
        if row is not None:
            return bool(row.is_allowed)

    # Guest/default fallback.
    guest_role = db.query(AppRole).filter(AppRole.name == AppRoleName.guest).first()
    if guest_role is None:
        return False
    guest_row = (
        db.query(RolePermission)
        .filter(RolePermission.role_id == guest_role.id, RolePermission.permission_id == perm.id)
        .first()
    )
    if guest_row is None:
        return False
    return bool(guest_row.is_allowed)
