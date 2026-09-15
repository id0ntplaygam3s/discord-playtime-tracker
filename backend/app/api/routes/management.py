from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, audit_actor_fields, require_permission
from app.api.guilds import resolve_guild_id
from app.core.permissions import PermissionCode
from app.core.config import get_settings
from app.services.settings_service import get_setting
from app.db.session import get_db
from app.models import Game, ManualPlaytime, ManualSource, PlaytimeAdjustment, User
from app.schemas.management import (
    CsvImportRequest,
    AdjustmentCreate,
    ManualPlaytimeCreate,
    SetAbsoluteTotalRequest,
    SteamImportPreviewRequest,
    SteamImportPreviewResponse,
    SteamImportRequest,
    SteamImportResponse,
)
from app.services.normalization import normalize_game_name
from app.services.management_service import (
    create_adjustment,
    create_manual_playtime,
    parse_csv_preview,
    set_absolute_total,
    to_seconds,
)
from app.services.session_service import write_audit_log
from app.services.session_service import get_or_create_game
from app.models import AuditAction
from app.services.game_identity_service import resolve_canonical_game
from app.services.steam_import import fetch_steam_owned_games

router = APIRouter(prefix="/management", tags=["management"])


def _create_new_custom_game(db: Session, title: str) -> Game:
    display_name = (title or "").strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="custom_game_title is required when override is enabled")

    normalized_base = normalize_game_name(display_name)
    if not normalized_base:
        raise HTTPException(status_code=400, detail="custom_game_title must contain letters or numbers")

    normalized_name = normalized_base
    suffix = 1
    while db.query(Game.id).filter(Game.normalized_name == normalized_name).first() is not None:
        suffix += 1
        normalized_name = f"{normalized_base}__manual__{suffix}"

    game = Game(normalized_name=normalized_name, display_name=display_name)
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


@router.get("/manual-playtime")
def list_manual_playtime(
    guild_id: int = Query(default=0),
    user_id: int | None = Query(default=None),
    game_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _=Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_ALL)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    query = db.query(ManualPlaytime, Game).join(Game, Game.id == ManualPlaytime.game_id).filter(
        ManualPlaytime.guild_id == guild_id,
        ManualPlaytime.deleted_at.is_(None),
    )
    if user_id:
        query = query.filter(ManualPlaytime.user_id == user_id)
    if game_id:
        query = query.filter(or_(ManualPlaytime.game_id == game_id, Game.canonical_game_id == game_id))

    manual_rows = query.order_by(ManualPlaytime.created_at.desc()).limit(limit).all()

    adjustments_q = (
        db.query(PlaytimeAdjustment, Game)
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(PlaytimeAdjustment.guild_id == guild_id)
    )
    if user_id:
        adjustments_q = adjustments_q.filter(PlaytimeAdjustment.user_id == user_id)
    if game_id:
        adjustments_q = adjustments_q.filter(or_(PlaytimeAdjustment.game_id == game_id, Game.canonical_game_id == game_id))
    adjustment_rows = adjustments_q.order_by(PlaytimeAdjustment.created_at.desc()).limit(limit).all()

    combined = [
        {
            "entry_kind": "manual",
            "id": row.id,
            "row_key": f"manual-{row.id}",
            "user_id": row.user_id,
            "game_id": row.game_id,
            "game_display_name": game.display_name,
            "canonical_game_id": game.canonical_game_id or game.id,
            "duration_seconds": row.duration_seconds,
            "source": row.source.value,
            "note": row.note,
            "created_at": row.created_at,
            "can_delete": True,
        }
        for row, game in manual_rows
    ] + [
        {
            "entry_kind": "adjustment",
            "id": row.id,
            "row_key": f"adjustment-{row.id}",
            "user_id": row.user_id,
            "game_id": row.game_id,
            "game_display_name": game.display_name,
            "canonical_game_id": game.canonical_game_id or game.id,
            "duration_seconds": row.adjustment_seconds,
            "source": "adjustment",
            "note": row.reason,
            "created_at": row.created_at,
            "can_delete": False,
        }
        for row, game in adjustment_rows
    ]

    combined.sort(key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return combined[:limit]


@router.get("/self/manual-playtime")
def list_own_manual_playtime(
    guild_id: int = Query(default=0),
    game_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: AuthUser = Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_OWN)),
    db: Session = Depends(get_db),
):
    if user.tracked_user_id is None and not user.is_legacy_admin:
        raise HTTPException(status_code=403, detail="Account principal required")
    guild_id = resolve_guild_id(db, guild_id)
    target_user_id = user.tracked_user_id
    if target_user_id is None and user.is_legacy_admin:
        target_user_id = db.query(User.id).filter(User.guild_id == guild_id).order_by(User.id.asc()).scalar()
    if target_user_id is None:
        return []
    manual_query = db.query(ManualPlaytime, Game).join(Game, Game.id == ManualPlaytime.game_id).filter(
        ManualPlaytime.guild_id == guild_id,
        ManualPlaytime.user_id == target_user_id,
        ManualPlaytime.deleted_at.is_(None),
    )
    if game_id:
        manual_query = manual_query.filter(or_(ManualPlaytime.game_id == game_id, Game.canonical_game_id == game_id))
    manual_rows = manual_query.order_by(ManualPlaytime.created_at.desc()).limit(limit).all()

    adjustments_q = (
        db.query(PlaytimeAdjustment, Game)
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(
            PlaytimeAdjustment.guild_id == guild_id,
            PlaytimeAdjustment.user_id == target_user_id,
        )
    )
    if game_id:
        adjustments_q = adjustments_q.filter(or_(PlaytimeAdjustment.game_id == game_id, Game.canonical_game_id == game_id))
    adjustment_rows = adjustments_q.order_by(PlaytimeAdjustment.created_at.desc()).limit(limit).all()

    combined = [
        {
            "entry_kind": "manual",
            "id": row.id,
            "row_key": f"manual-{row.id}",
            "user_id": row.user_id,
            "game_id": row.game_id,
            "game_display_name": game.display_name,
            "canonical_game_id": game.canonical_game_id or game.id,
            "duration_seconds": row.duration_seconds,
            "source": row.source.value,
            "note": row.note,
            "created_at": row.created_at,
            "can_delete": True,
        }
        for row, game in manual_rows
    ] + [
        {
            "entry_kind": "adjustment",
            "id": row.id,
            "row_key": f"adjustment-{row.id}",
            "user_id": row.user_id,
            "game_id": row.game_id,
            "game_display_name": game.display_name,
            "canonical_game_id": game.canonical_game_id or game.id,
            "duration_seconds": row.adjustment_seconds,
            "source": "adjustment",
            "note": row.reason,
            "created_at": row.created_at,
            "can_delete": False,
        }
        for row, game in adjustment_rows
    ]

    combined.sort(key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return combined[:limit]


@router.delete("/manual-playtime/{entry_id}")
def delete_manual_playtime(
    entry_id: int,
    guild_id: int = Query(default=0),
    admin=Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_ALL)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    row = (
        db.query(ManualPlaytime)
        .filter(ManualPlaytime.id == entry_id, ManualPlaytime.guild_id == guild_id, ManualPlaytime.deleted_at.is_(None))
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Manual playtime entry not found")

    row.deleted_at = datetime.now(timezone.utc)
    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.manual_playtime_soft_deleted,
        **audit_actor_fields(admin),
        target_user_id=row.user_id,
        target_game_id=row.game_id,
        change_seconds=-int(row.duration_seconds or 0),
        reason="Manual playtime entry deleted",
        metadata_json={"manual_playtime_id": row.id},
        commit=False,
    )
    db.commit()
    return {"ok": True, "deleted_manual_playtime_id": row.id}


@router.post("/manual-playtime")
def add_manual_playtime(
    payload: ManualPlaytimeCreate,
    admin=Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_ALL)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, payload.guild_id)
    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if payload.use_custom_game_title:
        if len(custom_title) > 255:
            raise HTTPException(status_code=400, detail="custom_game_title must be 255 characters or fewer")
        game = _create_new_custom_game(db, custom_title)
        game_id = game.id
    elif custom_title:
        raise HTTPException(status_code=400, detail="custom_game_title provided without enabling override")
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")

    selected_game = db.query(Game).filter(Game.id == game_id).first()
    if not selected_game:
        raise HTTPException(status_code=404, detail="Game not found")
    selected_game = resolve_canonical_game(db, selected_game)

    duration = to_seconds(payload.hours, payload.minutes)
    record = create_manual_playtime(
        db,
        guild_id=guild_id,
        user_id=payload.user_id,
        game_id=selected_game.id,
        duration_seconds=duration,
        source=payload.source,
        note=payload.note,
        created_by=admin.admin_user_id,
        actor_account_id=admin.account_id,
        actor_type="legacy_admin" if admin.is_legacy_admin else "account",
        actor_label=admin.username,
    )
    return {"id": record.id, "game_id": selected_game.id, "game_display_name": selected_game.display_name}


@router.post("/self/manual-playtime")
def add_own_manual_playtime(
    payload: ManualPlaytimeCreate,
    user: AuthUser = Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_OWN)),
    db: Session = Depends(get_db),
):
    if user.tracked_user_id is None and not user.is_legacy_admin:
        raise HTTPException(status_code=403, detail="Account principal required")
    can_create = bool(get_setting(db, "users_can_create_own_manual", True))
    if not can_create:
        raise HTTPException(status_code=403, detail="Users cannot create manual entries")
    guild_id = resolve_guild_id(db, payload.guild_id)
    if user.tracked_user_id is not None and payload.user_id != user.tracked_user_id:
        raise HTTPException(status_code=403, detail="Cannot create playtime for another user")

    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if payload.use_custom_game_title:
        if len(custom_title) > 255:
            raise HTTPException(status_code=400, detail="custom_game_title must be 255 characters or fewer")
        game = _create_new_custom_game(db, custom_title)
        game_id = game.id
    elif custom_title:
        raise HTTPException(status_code=400, detail="custom_game_title provided without enabling override")
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")

    selected_game = db.query(Game).filter(Game.id == game_id).first()
    if not selected_game:
        raise HTTPException(status_code=404, detail="Game not found")
    selected_game = resolve_canonical_game(db, selected_game)

    duration = to_seconds(payload.hours, payload.minutes)
    row = create_manual_playtime(
        db,
        guild_id=guild_id,
        user_id=payload.user_id,
        game_id=selected_game.id,
        duration_seconds=duration,
        source=payload.source,
        note=payload.note,
        created_by=None,
        actor_account_id=user.account_id,
        actor_type="account",
        actor_label=user.username,
    )
    return {"id": row.id, "game_id": selected_game.id, "game_display_name": selected_game.display_name}


@router.delete("/self/manual-playtime/{entry_id}")
def delete_own_manual_playtime(
    entry_id: int,
    guild_id: int = Query(default=0),
    user: AuthUser = Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_OWN)),
    db: Session = Depends(get_db),
):
    if user.tracked_user_id is None and not user.is_legacy_admin:
        raise HTTPException(status_code=403, detail="Account principal required")
    can_delete = bool(get_setting(db, "users_can_delete_own_manual", True))
    if not can_delete:
        raise HTTPException(status_code=403, detail="Users cannot delete manual entries")

    guild_id = resolve_guild_id(db, guild_id)
    row_query = (
        db.query(ManualPlaytime)
        .filter(
            ManualPlaytime.id == entry_id,
            ManualPlaytime.guild_id == guild_id,
            ManualPlaytime.deleted_at.is_(None),
        )
    )
    if user.tracked_user_id is not None:
        row_query = row_query.filter(ManualPlaytime.user_id == user.tracked_user_id)
    row = row_query.first()
    if not row:
        raise HTTPException(status_code=404, detail="Manual playtime entry not found")
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "deleted_manual_playtime_id": row.id}


@router.post("/adjustments")
def add_adjustment(payload: AdjustmentCreate, admin=Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_ALL)), db: Session = Depends(get_db)):
    guild_id = resolve_guild_id(db, payload.guild_id)
    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if payload.use_custom_game_title:
        if len(custom_title) > 255:
            raise HTTPException(status_code=400, detail="custom_game_title must be 255 characters or fewer")
        game = _create_new_custom_game(db, custom_title)
        game_id = game.id
    elif custom_title:
        raise HTTPException(status_code=400, detail="custom_game_title provided without enabling override")
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")

    selected_game = db.query(Game).filter(Game.id == game_id).first()
    if not selected_game:
        raise HTTPException(status_code=404, detail="Game not found")
    selected_game = resolve_canonical_game(db, selected_game)

    seconds = to_seconds(abs(payload.hours), abs(payload.minutes)) * (1 if payload.sign >= 0 else -1)
    try:
        row = create_adjustment(
            db,
            guild_id=guild_id,
            user_id=payload.user_id,
            game_id=selected_game.id,
            adjustment_seconds=seconds,
            reason=payload.reason,
            created_by=admin.admin_user_id,
            actor_account_id=admin.account_id,
            actor_type="legacy_admin" if admin.is_legacy_admin else "account",
            actor_label=admin.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": row.id,
        "adjustment_seconds": row.adjustment_seconds,
        "game_id": selected_game.id,
        "game_display_name": selected_game.display_name,
    }


@router.post("/self/adjustments")
def add_own_adjustment(
    payload: AdjustmentCreate,
    user: AuthUser = Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_OWN)),
    db: Session = Depends(get_db),
):
    if user.tracked_user_id is None and not user.is_legacy_admin:
        raise HTTPException(status_code=403, detail="Account principal required")
    guild_id = resolve_guild_id(db, payload.guild_id)
    if user.tracked_user_id is not None and payload.user_id != user.tracked_user_id:
        raise HTTPException(status_code=403, detail="Cannot create adjustment for another user")

    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if payload.use_custom_game_title:
        if len(custom_title) > 255:
            raise HTTPException(status_code=400, detail="custom_game_title must be 255 characters or fewer")
        game = _create_new_custom_game(db, custom_title)
        game_id = game.id
    elif custom_title:
        raise HTTPException(status_code=400, detail="custom_game_title provided without enabling override")
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")

    selected_game = db.query(Game).filter(Game.id == game_id).first()
    if not selected_game:
        raise HTTPException(status_code=404, detail="Game not found")
    selected_game = resolve_canonical_game(db, selected_game)

    seconds = to_seconds(abs(payload.hours), abs(payload.minutes)) * (1 if payload.sign >= 0 else -1)
    try:
        row = create_adjustment(
            db,
            guild_id=guild_id,
            user_id=payload.user_id,
            game_id=selected_game.id,
            adjustment_seconds=seconds,
            reason=payload.reason,
            created_by=None,
            actor_account_id=user.account_id,
            actor_type="account",
            actor_label=user.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": row.id,
        "adjustment_seconds": row.adjustment_seconds,
        "game_id": selected_game.id,
        "game_display_name": selected_game.display_name,
    }


@router.post("/set-total")
def set_total(payload: SetAbsoluteTotalRequest, admin=Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_ALL)), db: Session = Depends(get_db)):
    guild_id = resolve_guild_id(db, payload.guild_id)
    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if payload.use_custom_game_title:
        if len(custom_title) > 255:
            raise HTTPException(status_code=400, detail="custom_game_title must be 255 characters or fewer")
        game = _create_new_custom_game(db, custom_title)
        game_id = game.id
    elif custom_title:
        raise HTTPException(status_code=400, detail="custom_game_title provided without enabling override")
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")

    selected_game = db.query(Game).filter(Game.id == game_id).first()
    if not selected_game:
        raise HTTPException(status_code=404, detail="Game not found")
    selected_game = resolve_canonical_game(db, selected_game)

    try:
        adjustment = set_absolute_total(
            db,
            guild_id=guild_id,
            user_id=payload.user_id,
            game_id=selected_game.id,
            desired_total_seconds=payload.desired_total_seconds,
            reason=payload.reason,
            created_by=admin.admin_user_id,
            actor_account_id=admin.account_id,
            actor_type="legacy_admin" if admin.is_legacy_admin else "account",
            actor_label=admin.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": adjustment.id,
        "delta_seconds": adjustment.adjustment_seconds,
        "game_id": selected_game.id,
        "game_display_name": selected_game.display_name,
    }


@router.post("/self/set-total")
def set_own_total(
    payload: SetAbsoluteTotalRequest,
    user: AuthUser = Depends(require_permission(PermissionCode.PLAYTIME_MANAGE_OWN)),
    db: Session = Depends(get_db),
):
    if user.tracked_user_id is None and not user.is_legacy_admin:
        raise HTTPException(status_code=403, detail="Account principal required")
    guild_id = resolve_guild_id(db, payload.guild_id)
    if user.tracked_user_id is not None and payload.user_id != user.tracked_user_id:
        raise HTTPException(status_code=403, detail="Cannot set total for another user")

    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if payload.use_custom_game_title:
        if len(custom_title) > 255:
            raise HTTPException(status_code=400, detail="custom_game_title must be 255 characters or fewer")
        game = _create_new_custom_game(db, custom_title)
        game_id = game.id
    elif custom_title:
        raise HTTPException(status_code=400, detail="custom_game_title provided without enabling override")
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")

    selected_game = db.query(Game).filter(Game.id == game_id).first()
    if not selected_game:
        raise HTTPException(status_code=404, detail="Game not found")
    selected_game = resolve_canonical_game(db, selected_game)

    try:
        adjustment = set_absolute_total(
            db,
            guild_id=guild_id,
            user_id=payload.user_id,
            game_id=selected_game.id,
            desired_total_seconds=payload.desired_total_seconds,
            reason=payload.reason,
            created_by=None,
            actor_account_id=user.account_id,
            actor_type="account",
            actor_label=user.username,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "id": adjustment.id,
        "delta_seconds": adjustment.adjustment_seconds,
        "game_id": selected_game.id,
        "game_display_name": selected_game.display_name,
    }


@router.post("/csv/preview")
def csv_preview(file: UploadFile = File(...), _=Depends(require_permission(PermissionCode.IMPORTS_MANAGE))):
    content = file.file.read()
    rows, errors = parse_csv_preview(content)
    return {
        "valid_rows": rows,
        "invalid_rows": [{"row_number": e.row_number, "message": e.message} for e in errors],
    }


@router.post("/csv/import")
def csv_import(
    payload: CsvImportRequest,
    admin=Depends(require_permission(PermissionCode.IMPORTS_MANAGE)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, payload.guild_id)
    all_or_nothing = payload.all_or_nothing
    import_mode = payload.import_mode
    rows = payload.rows

    imported = 0
    errors = []
    tx = db.begin_nested() if all_or_nothing else None

    try:
        for idx, row in enumerate(rows, start=1):
            discord_user_id = row.get("discord_user_id")
            user = None
            if discord_user_id is not None:
                user = db.query(User).filter(User.guild_id == guild_id, User.discord_user_id == int(discord_user_id)).first()
            if not user and row.get("discord_user"):
                user = (
                    db.query(User)
                    .filter(
                        User.guild_id == guild_id,
                        or_(User.display_name == row["discord_user"], User.username == row["discord_user"]),
                    )
                    .first()
                )
            if not user:
                errors.append({"row": idx, "error": "User not found"})
                if all_or_nothing:
                    raise ValueError("Import aborted due to validation errors")
                continue

            game = get_or_create_game(db, row["game"], None, None, commit=not all_or_nothing)
            duration_seconds = to_seconds(int(row["hours"]), int(row["minutes"]))
            if import_mode == "overwrite":
                set_absolute_total(
                    db,
                    guild_id=guild_id,
                    user_id=user.id,
                    game_id=game.id,
                    desired_total_seconds=duration_seconds,
                    reason=row.get("note") or "CSV overwrite import",
                    created_by=admin.admin_user_id,
                    actor_account_id=admin.account_id,
                    actor_type="legacy_admin" if admin.is_legacy_admin else "account",
                    actor_label=admin.username,
                    commit=not all_or_nothing,
                )
            else:
                create_manual_playtime(
                    db,
                    guild_id=guild_id,
                    user_id=user.id,
                    game_id=game.id,
                    duration_seconds=duration_seconds,
                    source=ManualSource(row["source"]),
                    note=row.get("note"),
                    created_by=admin.admin_user_id,
                    actor_account_id=admin.account_id,
                    actor_type="legacy_admin" if admin.is_legacy_admin else "account",
                    actor_label=admin.username,
                    commit=not all_or_nothing,
                )
            imported += 1

        if all_or_nothing:
            write_audit_log(
                db,
                guild_id=guild_id,
                action=AuditAction.csv_import,
                **audit_actor_fields(admin),
                target_user_id=None,
                target_game_id=None,
                change_seconds=None,
                reason=f"CSV import completed ({imported} rows)",
                metadata_json={"imported_rows": imported, "all_or_nothing": True, "import_mode": import_mode},
                commit=False,
            )
            tx.commit()
            db.commit()
        elif imported > 0:
            write_audit_log(
                db,
                guild_id=guild_id,
                action=AuditAction.csv_import,
                **audit_actor_fields(admin),
                target_user_id=None,
                target_game_id=None,
                change_seconds=None,
                reason=f"CSV import completed ({imported} rows)",
                metadata_json={"imported_rows": imported, "all_or_nothing": False, "import_mode": import_mode},
                commit=True,
            )
    except Exception as exc:
        if tx:
            if tx.is_active:
                tx.rollback()
            else:
                db.rollback()
        raise HTTPException(status_code=400, detail=f"Import failed: {exc}") from exc

    return {"imported": imported, "errors": errors}


@router.post("/steam/preview", response_model=SteamImportPreviewResponse)
def steam_preview(
    payload: SteamImportPreviewRequest,
    _=Depends(require_permission(PermissionCode.IMPORTS_MANAGE)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, payload.guild_id)
    settings = get_settings()
    if not settings.steam_api_key:
        raise HTTPException(status_code=400, detail="STEAM_API_KEY is not configured")

    user = db.query(User).filter(User.id == payload.user_id, User.guild_id == guild_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        preview = fetch_steam_owned_games(payload.steam_profile, settings.steam_api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Steam import preview failed: {exc}") from exc

    games = [
        {
            "appid": game.appid,
            "name": game.name,
            "playtime_minutes": game.playtime_minutes,
            "duration_seconds": game.playtime_minutes * 60,
        }
        for game in preview.games
    ]
    return SteamImportPreviewResponse(
        steam_id=preview.steam_id,
        profile_label=preview.profile_label,
        total_games=len(games),
        games=games,
    )


@router.post("/steam/import", response_model=SteamImportResponse)
def steam_import(
    payload: SteamImportRequest,
    admin=Depends(require_permission(PermissionCode.IMPORTS_MANAGE)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, payload.guild_id)
    settings = get_settings()
    if not settings.steam_api_key:
        raise HTTPException(status_code=400, detail="STEAM_API_KEY is not configured")

    user = db.query(User).filter(User.id == payload.user_id, User.guild_id == guild_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        preview = fetch_steam_owned_games(payload.steam_profile, settings.steam_api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Steam import failed: {exc}") from exc

    import_tag = f"[steam-import:{preview.steam_id}]"
    imported = 0
    replaced = 0
    tx = db.begin_nested()

    try:
        if payload.replace_previous:
            replaced = (
                db.query(ManualPlaytime)
                .filter(
                    ManualPlaytime.guild_id == guild_id,
                    ManualPlaytime.user_id == payload.user_id,
                    ManualPlaytime.source == ManualSource.imported,
                    ManualPlaytime.deleted_at.is_(None),
                    ManualPlaytime.note.like(f"{import_tag}%"),
                )
                .update({ManualPlaytime.deleted_at: datetime.now(timezone.utc)}, synchronize_session=False)
            )

        for game in preview.games[: payload.max_games]:
            db_game = get_or_create_game(db, game.name, game.appid, None, commit=False)
            note = f"{import_tag} steam_appid={game.appid} profile={preview.profile_label}"
            create_manual_playtime(
                db,
                guild_id=guild_id,
                user_id=payload.user_id,
                game_id=db_game.id,
                duration_seconds=game.playtime_minutes * 60,
                source=ManualSource.imported,
                note=note,
                created_by=admin.admin_user_id,
                actor_account_id=admin.account_id,
                actor_type="legacy_admin" if admin.is_legacy_admin else "account",
                actor_label=admin.username,
                commit=False,
            )
            imported += 1

        write_audit_log(
            db,
            guild_id=guild_id,
            action=AuditAction.csv_import,
            **audit_actor_fields(admin),
            target_user_id=payload.user_id,
            target_game_id=None,
            change_seconds=None,
            reason=f"Steam import from {preview.profile_label} ({imported} games)",
            metadata_json={"steam_id": preview.steam_id, "imported": imported, "replaced": replaced},
            commit=False,
        )

        tx.commit()
        db.commit()
    except Exception as exc:
        if tx.is_active:
            tx.rollback()
        else:
            db.rollback()
        raise HTTPException(status_code=400, detail=f"Steam import failed: {exc}") from exc

    return SteamImportResponse(imported=imported, replaced=replaced, steam_id=preview.steam_id)
