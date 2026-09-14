from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.api.guilds import resolve_guild_id
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Game, ManualPlaytime, ManualSource, User
from app.schemas.management import (
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
from app.services.steam_import import fetch_steam_owned_games

router = APIRouter(prefix="/management", tags=["management"])


@router.get("/manual-playtime")
def list_manual_playtime(
    guild_id: int = Query(default=0),
    user_id: int | None = Query(default=None),
    game_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    query = db.query(ManualPlaytime).filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.deleted_at.is_(None))
    if user_id:
        query = query.filter(ManualPlaytime.user_id == user_id)
    if game_id:
        query = query.filter(ManualPlaytime.game_id == game_id)

    rows = query.order_by(ManualPlaytime.created_at.desc()).limit(limit).all()
    return [
        {
            "id": row.id,
            "user_id": row.user_id,
            "game_id": row.game_id,
            "duration_seconds": row.duration_seconds,
            "source": row.source.value,
            "note": row.note,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.delete("/manual-playtime/{entry_id}")
def delete_manual_playtime(
    entry_id: int,
    guild_id: int = Query(default=0),
    admin=Depends(require_admin),
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
        admin_user_id=admin.id,
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
def add_manual_playtime(payload: ManualPlaytimeCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    guild_id = resolve_guild_id(db, payload.guild_id)
    game_id = payload.game_id
    custom_title = (payload.custom_game_title or "").strip()
    if custom_title:
        game = get_or_create_game(db, custom_title, None, None)
        game_id = game.id
    if not game_id:
        raise HTTPException(status_code=400, detail="Select a game or provide a custom game title")
    duration = to_seconds(payload.hours, payload.minutes)
    record = create_manual_playtime(
        db,
        guild_id=guild_id,
        user_id=payload.user_id,
        game_id=game_id,
        duration_seconds=duration,
        source=payload.source,
        note=payload.note,
        created_by=admin.id,
    )
    return {"id": record.id}


@router.post("/adjustments")
def add_adjustment(payload: AdjustmentCreate, admin=Depends(require_admin), db: Session = Depends(get_db)):
    guild_id = resolve_guild_id(db, payload.guild_id)
    seconds = to_seconds(abs(payload.hours), abs(payload.minutes)) * (1 if payload.sign >= 0 else -1)
    try:
        row = create_adjustment(
            db,
            guild_id=guild_id,
            user_id=payload.user_id,
            game_id=payload.game_id,
            adjustment_seconds=seconds,
            reason=payload.reason,
            created_by=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": row.id, "adjustment_seconds": row.adjustment_seconds}


@router.post("/set-total")
def set_total(payload: SetAbsoluteTotalRequest, admin=Depends(require_admin), db: Session = Depends(get_db)):
    guild_id = resolve_guild_id(db, payload.guild_id)
    try:
        adjustment = set_absolute_total(
            db,
            guild_id=guild_id,
            user_id=payload.user_id,
            game_id=payload.game_id,
            desired_total_seconds=payload.desired_total_seconds,
            reason=payload.reason,
            created_by=admin.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"id": adjustment.id, "delta_seconds": adjustment.adjustment_seconds}


@router.post("/csv/preview")
def csv_preview(file: UploadFile = File(...), _=Depends(require_admin)):
    content = file.file.read()
    rows, errors = parse_csv_preview(content)
    return {
        "valid_rows": rows,
        "invalid_rows": [{"row_number": e.row_number, "message": e.message} for e in errors],
    }


@router.post("/csv/import")
def csv_import(
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))
    all_or_nothing = bool(payload.get("all_or_nothing", True))
    rows = payload.get("rows", [])

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

            if all_or_nothing:
                normalized = normalize_game_name(row["game"])
                game = db.query(Game).filter(Game.normalized_name == normalized).first()
                if not game:
                    game = Game(normalized_name=normalized, display_name=row["game"])
                    db.add(game)
                    db.flush()
            else:
                game = get_or_create_game(db, row["game"], None, None)
            create_manual_playtime(
                db,
                guild_id=guild_id,
                user_id=user.id,
                game_id=game.id,
                duration_seconds=to_seconds(int(row["hours"]), int(row["minutes"])),
                source=ManualSource(row["source"]),
                note=row.get("note"),
                created_by=admin.id,
                commit=not all_or_nothing,
            )
            imported += 1

        if all_or_nothing:
            write_audit_log(
                db,
                guild_id=guild_id,
                action=AuditAction.csv_import,
                admin_user_id=admin.id,
                target_user_id=None,
                target_game_id=None,
                change_seconds=None,
                reason=f"CSV import completed ({imported} rows)",
                metadata_json={"imported_rows": imported, "all_or_nothing": True},
                commit=False,
            )
            tx.commit()
            db.commit()
        elif imported > 0:
            write_audit_log(
                db,
                guild_id=guild_id,
                action=AuditAction.csv_import,
                admin_user_id=admin.id,
                target_user_id=None,
                target_game_id=None,
                change_seconds=None,
                reason=f"CSV import completed ({imported} rows)",
                metadata_json={"imported_rows": imported, "all_or_nothing": False},
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
    _=Depends(require_admin),
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
    admin=Depends(require_admin),
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
                created_by=admin.id,
                commit=False,
            )
            imported += 1

        write_audit_log(
            db,
            guild_id=guild_id,
            action=AuditAction.csv_import,
            admin_user_id=admin.id,
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
