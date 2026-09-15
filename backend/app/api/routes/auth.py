from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, audit_actor_fields, get_current_user, require_admin
from app.core.permissions import PermissionCode
from app.core.config import get_settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models import (
    AccountStatus,
    AdminUser,
    AppRole,
    AppRoleName,
    AuditAction,
    PasswordResetRequest,
    PasswordResetStatus,
    Role,
    User,
    UserAccount,
)
from app.schemas.auth import (
    AccountLoginRequest,
    LoginRequest,
    MeResponse,
    PasswordResetCompleteRequest,
    PasswordResetRequestPayload,
    RegisterOptionsUser,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
)
from app.services.authz_service import resolve_permission
from app.services.authz_service import ensure_roles_and_permissions
from app.services.session_service import write_audit_log
from app.services.settings_service import get_setting

router = APIRouter(prefix="/auth", tags=["auth"])


def _validate_password(db: Session, password: str, confirm_password: str) -> None:
    min_length = int(get_setting(db, "auth_min_password_length", 8) or 8)
    if len(password) < min_length:
        raise HTTPException(status_code=400, detail=f"Password must be at least {min_length} characters")
    if password != confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")


def _issue_account_token(account: UserAccount, user: User) -> str:
    settings = get_settings()
    return create_access_token(
        subject=str(account.id),
        secret_key=settings.secret_key,
        expires_minutes=settings.access_token_expire_minutes,
        extra_claims={
            "typ": "account",
            "aid": account.id,
            "uid": user.id,
            "role": account.role.name.value,
        },
    )


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
        extra_claims={"role": user.role.value, "typ": "legacy_admin"},
    )
    return TokenResponse(access_token=token)


@router.post("/account-login", response_model=TokenResponse)
def account_login(payload: AccountLoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    account_row = (
        db.query(UserAccount, User)
        .join(User, User.id == UserAccount.user_id)
        .filter(User.id == payload.user_id)
        .first()
    )
    if not account_row:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    account, user = account_row

    if account.status == AccountStatus.pending:
        raise HTTPException(status_code=403, detail="Account is pending approval")
    if account.status == AccountStatus.disabled:
        raise HTTPException(status_code=403, detail="Account is disabled")
    if account.status == AccountStatus.locked and account.locked_until and account.locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=403, detail="Account is locked")
    if account.status == AccountStatus.locked and account.locked_until and account.locked_until <= datetime.now(timezone.utc):
        account.status = AccountStatus.active
        account.locked_until = None
        account.failed_login_attempts = 0

    if not verify_password(payload.password, account.password_hash):
        max_attempts = int(get_setting(db, "auth_max_failed_login_attempts", 5) or 5)
        lock_minutes = int(get_setting(db, "auth_lock_minutes", 30) or 30)
        account.failed_login_attempts = int(account.failed_login_attempts or 0) + 1
        if account.failed_login_attempts >= max_attempts:
            account.status = AccountStatus.locked
            account.locked_until = datetime.now(timezone.utc) + timedelta(minutes=lock_minutes)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    account.failed_login_attempts = 0
    account.last_login_at = datetime.now(timezone.utc)
    if account.status != AccountStatus.active:
        account.status = AccountStatus.active
    db.commit()

    return TokenResponse(access_token=_issue_account_token(account, user))


@router.get("/registration-options", response_model=list[RegisterOptionsUser])
def registration_options(db: Session = Depends(get_db)):
    registration_enabled = bool(get_setting(db, "registration_enabled", True))
    if not registration_enabled:
        raise HTTPException(status_code=403, detail="Registration is disabled")

    rows = (
        db.query(User)
        .outerjoin(UserAccount, UserAccount.user_id == User.id)
        .filter(User.is_active.is_(True), UserAccount.id.is_(None))
        .order_by(User.display_name.asc())
        .all()
    )
    return [
        RegisterOptionsUser(id=row.id, username=row.username, display_name=row.display_name)
        for row in rows
    ]


@router.get("/account-options")
def account_options(db: Session = Depends(get_db)):
    rows = (
        db.query(User, UserAccount)
        .join(UserAccount, UserAccount.user_id == User.id)
        .filter(User.is_active.is_(True))
        .order_by(User.display_name.asc())
        .all()
    )
    return [
        {
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "status": account.status.value,
        }
        for user, account in rows
    ]


@router.post("/register", response_model=RegisterResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> RegisterResponse:
    registration_enabled = bool(get_setting(db, "registration_enabled", True))
    if not registration_enabled:
        raise HTTPException(status_code=403, detail="Registration is disabled")

    _validate_password(db, payload.password, payload.confirm_password)

    tracked_user = db.query(User).filter(User.id == payload.user_id, User.is_active.is_(True)).first()
    if not tracked_user:
        raise HTTPException(status_code=400, detail="Invalid user selection")

    existing = db.query(UserAccount).filter(UserAccount.user_id == payload.user_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists for that Discord user")

    ensure_roles_and_permissions(db)

    default_role_name = str(get_setting(db, "default_registration_role", "user") or "user")
    try:
        role_key = AppRoleName(default_role_name)
    except ValueError:
        role_key = AppRoleName.user
    role = db.query(AppRole).filter(AppRole.name == role_key).first()
    if role is None:
        role = db.query(AppRole).filter(AppRole.name == AppRoleName.user).first()
    if role is None:
        raise HTTPException(status_code=500, detail="Role configuration is invalid")

    account = UserAccount(
        user_id=tracked_user.id,
        role_id=role.id,
        password_hash=hash_password(payload.password),
        status=AccountStatus.pending,
    )
    db.add(account)
    db.flush()

    write_audit_log(
        db,
        guild_id=tracked_user.guild_id,
        action=AuditAction.registration_submitted,
        admin_user_id=None,
        target_user_id=tracked_user.id,
        target_game_id=None,
        change_seconds=None,
        reason="Registration submitted",
        metadata_json={"account_id": account.id},
        commit=False,
    )
    db.commit()
    return RegisterResponse(status="pending")


@router.get("/registrations")
def list_pending_registrations(admin: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    rows = (
        db.query(UserAccount, User, AppRole)
        .join(User, User.id == UserAccount.user_id)
        .join(AppRole, AppRole.id == UserAccount.role_id)
        .filter(UserAccount.status == AccountStatus.pending)
        .order_by(UserAccount.created_at.asc())
        .all()
    )
    return [
        {
            "account_id": account.id,
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "status": account.status.value,
            "requested_at": account.created_at,
            "role": role.name.value,
        }
        for account, user, role in rows
    ]


@router.post("/registrations/{account_id}/approve")
def approve_registration(account_id: int, admin: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    account_row = (
        db.query(UserAccount, User)
        .join(User, User.id == UserAccount.user_id)
        .filter(UserAccount.id == account_id)
        .first()
    )
    if not account_row:
        raise HTTPException(status_code=404, detail="Registration not found")
    account, user = account_row
    if account.status != AccountStatus.pending:
        raise HTTPException(status_code=400, detail="Registration is not pending")

    account.status = AccountStatus.active
    account.approved_at = datetime.now(timezone.utc)
    account.approved_by_admin_user_id = admin.admin_user_id
    account.rejected_at = None
    account.rejected_by_admin_user_id = None

    write_audit_log(
        db,
        guild_id=user.guild_id,
        action=AuditAction.registration_approved,
        **audit_actor_fields(admin),
        target_user_id=user.id,
        target_game_id=None,
        change_seconds=None,
        reason="Registration approved",
        metadata_json={"account_id": account.id},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.post("/registrations/{account_id}/reject")
def reject_registration(account_id: int, admin: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    account_row = (
        db.query(UserAccount, User)
        .join(User, User.id == UserAccount.user_id)
        .filter(UserAccount.id == account_id)
        .first()
    )
    if not account_row:
        raise HTTPException(status_code=404, detail="Registration not found")
    account, user = account_row
    if account.status != AccountStatus.pending:
        raise HTTPException(status_code=400, detail="Registration is not pending")

    account.status = AccountStatus.disabled
    account.rejected_at = datetime.now(timezone.utc)
    account.rejected_by_admin_user_id = admin.admin_user_id

    write_audit_log(
        db,
        guild_id=user.guild_id,
        action=AuditAction.registration_rejected,
        **audit_actor_fields(admin),
        target_user_id=user.id,
        target_game_id=None,
        change_seconds=None,
        reason="Registration rejected",
        metadata_json={"account_id": account.id},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.post("/guest", response_model=TokenResponse)
def guest_login(db: Session = Depends(get_db)) -> TokenResponse:
    guest_enabled = bool(get_setting(db, "guest_access_enabled", True))
    if not guest_enabled:
        raise HTTPException(status_code=403, detail="Guest access is disabled")

    settings = get_settings()
    token = create_access_token(
        "guest",
        settings.secret_key,
        settings.access_token_expire_minutes,
        extra_claims={"role": Role.viewer.value, "guest": True},
    )
    return TokenResponse(access_token=token)


@router.post("/password-resets/request")
def request_password_reset(payload: PasswordResetRequestPayload, db: Session = Depends(get_db)):
    account_row = (
        db.query(UserAccount, User)
        .join(User, User.id == UserAccount.user_id)
        .filter(User.id == payload.user_id)
        .first()
    )
    if account_row:
        account, user = account_row
        row = PasswordResetRequest(account_id=account.id, status=PasswordResetStatus.pending)
        db.add(row)
        write_audit_log(
            db,
            guild_id=user.guild_id,
            action=AuditAction.password_reset_requested,
            admin_user_id=None,
            target_user_id=user.id,
            target_game_id=None,
            change_seconds=None,
            reason="Password reset requested",
            metadata_json={"request_id": None},
            commit=False,
        )
    db.commit()
    # Avoid account enumeration by always returning success.
    return {"ok": True}


@router.get("/password-resets")
def list_password_reset_requests(admin: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    _ = admin
    rows = (
        db.query(PasswordResetRequest, UserAccount, User)
        .join(UserAccount, UserAccount.id == PasswordResetRequest.account_id)
        .join(User, User.id == UserAccount.user_id)
        .filter(PasswordResetRequest.status == PasswordResetStatus.pending)
        .order_by(PasswordResetRequest.created_at.asc())
        .all()
    )
    return [
        {
            "request_id": req.id,
            "account_id": account.id,
            "user_id": user.id,
            "username": user.username,
            "display_name": user.display_name,
            "status": req.status.value,
            "created_at": req.created_at,
        }
        for req, account, user in rows
    ]


@router.post("/password-resets/{request_id}/approve")
def approve_password_reset(request_id: int, admin: AuthUser = Depends(require_admin), db: Session = Depends(get_db)):
    row = (
        db.query(PasswordResetRequest, UserAccount, User)
        .join(UserAccount, UserAccount.id == PasswordResetRequest.account_id)
        .join(User, User.id == UserAccount.user_id)
        .filter(PasswordResetRequest.id == request_id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Reset request not found")
    req, account, user = row
    if req.status != PasswordResetStatus.pending:
        raise HTTPException(status_code=400, detail="Reset request is not pending")

    token = secrets.token_urlsafe(32)
    req.token_hash = hash_password(token)
    req.status = PasswordResetStatus.approved
    req.approved_by_admin_user_id = admin.admin_user_id
    req.expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    write_audit_log(
        db,
        guild_id=user.guild_id,
        action=AuditAction.password_reset_approved,
        **audit_actor_fields(admin),
        target_user_id=user.id,
        target_game_id=None,
        change_seconds=None,
        reason="Password reset approved",
        metadata_json={"request_id": req.id},
        commit=False,
    )
    db.commit()
    # Token is returned once to admin to share out-of-band.
    return {"ok": True, "reset_token": token, "expires_at": req.expires_at}


@router.post("/password-resets/complete")
def complete_password_reset(payload: PasswordResetCompleteRequest, db: Session = Depends(get_db)):
    _validate_password(db, payload.new_password, payload.confirm_password)

    now = datetime.now(timezone.utc)
    rows = (
        db.query(PasswordResetRequest, UserAccount, User)
        .join(UserAccount, UserAccount.id == PasswordResetRequest.account_id)
        .join(User, User.id == UserAccount.user_id)
        .filter(PasswordResetRequest.status == PasswordResetStatus.approved)
        .all()
    )
    target = None
    for req, account, user in rows:
        if req.expires_at and req.expires_at < now:
            req.status = PasswordResetStatus.expired
            continue
        if req.token_hash and verify_password(payload.token, req.token_hash):
            target = (req, account, user)
            break

    if target is None:
        db.commit()
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    req, account, user = target
    account.password_hash = hash_password(payload.new_password)
    account.failed_login_attempts = 0
    account.locked_until = None
    if account.status in {AccountStatus.locked, AccountStatus.disabled, AccountStatus.pending}:
        account.status = AccountStatus.active
    req.status = PasswordResetStatus.completed
    req.completed_at = now
    req.token_hash = None

    write_audit_log(
        db,
        guild_id=user.guild_id,
        action=AuditAction.password_reset_completed,
        admin_user_id=None,
        target_user_id=user.id,
        target_game_id=None,
        change_seconds=None,
        reason="Password reset completed",
        metadata_json={"request_id": req.id},
        commit=False,
    )
    db.commit()
    return {"ok": True}


@router.get("/me", response_model=MeResponse)
def me(user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> MeResponse:
    permission_codes: list[str] = []
    for code in (
        PermissionCode.DASHBOARD_VIEW,
        PermissionCode.GAMES_VIEW,
        PermissionCode.USERS_VIEW,
        PermissionCode.USERS_MANAGE,
        PermissionCode.PLAYTIME_VIEW,
        PermissionCode.PLAYTIME_MANAGE_OWN,
        PermissionCode.PLAYTIME_MANAGE_ALL,
        PermissionCode.IMPORTS_VIEW,
        PermissionCode.IMPORTS_MANAGE,
        PermissionCode.AUDIT_VIEW,
        PermissionCode.REGISTRATIONS_VIEW,
        PermissionCode.REGISTRATIONS_MANAGE,
        PermissionCode.SETTINGS_VIEW,
        PermissionCode.SETTINGS_MANAGE,
        PermissionCode.ACCOUNTS_RESET_PASSWORD,
        PermissionCode.ACCOUNTS_UNLOCK,
        PermissionCode.ACCOUNTS_DISABLE,
        PermissionCode.PERMISSIONS_VIEW,
        PermissionCode.PERMISSIONS_MANAGE,
    ):
        if resolve_permission(
            db,
            code,
            is_guest=user.is_guest,
            is_legacy_admin=user.is_legacy_admin,
            account_id=user.account_id,
            role_id=user.role_id,
        ):
            permission_codes.append(code)

    account_status = None
    if user.account_id:
        account = db.query(UserAccount).filter(UserAccount.id == user.account_id).first()
        if account is not None:
            account_status = account.status.value

    return MeResponse(
        username=user.username,
        role=user.role.value,
        role_name=user.role_name,
        is_guest=user.is_guest,
        account_status=account_status,
        tracked_user_id=user.tracked_user_id,
        permissions=permission_codes,
    )
