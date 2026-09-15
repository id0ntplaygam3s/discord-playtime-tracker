from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, audit_actor_fields, require_admin, require_permission
from app.core.permissions import PermissionCode
from app.core.config import get_settings
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.models import ActivitySession, AuditAction, Game, GameAlias, GameMergeSuggestionState, ManualPlaytime, MergeSuggestionStatus, PlaytimeAdjustment, User
from app.services.date_ranges import resolve_range
from app.services import stats_service
from app.services.session_service import write_audit_log
from app.services.normalization import normalize_game_name
from app.services.game_identity_service import add_alias_if_missing, resolve_canonical_game, suggest_merge_pairs

router = APIRouter(prefix="/games", tags=["games"])


def _duration_seconds_expr(db: Session):
    if db.bind and db.bind.dialect.name == "sqlite":
        return (func.julianday(ActivitySession.ended_at) - func.julianday(ActivitySession.started_at)) * 86400
    return func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)


def _game_has_guild_data(db: Session, guild_id: int, game_id: int) -> bool:
    resolved_id = game_id
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is not None:
        resolved_id = resolve_canonical_game(db, game).id
    return bool(
        db.query(ActivitySession.id)
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id)
        .first()
        or db.query(ManualPlaytime.id)
        .join(Game, Game.id == ManualPlaytime.game_id)
        .filter(ManualPlaytime.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id)
        .first()
        or db.query(PlaytimeAdjustment.id)
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(PlaytimeAdjustment.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id)
        .first()
    )


@router.get("")
def list_games(
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(require_permission(PermissionCode.GAMES_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    ranked = stats_service.ranked_games(db, guild_id, source="combined", limit=5000)
    ranked_ids = [int(item["id"]) for item in ranked]
    if not ranked_ids:
        return []

    rows = db.query(Game).filter(Game.id.in_(ranked_ids), Game.is_hidden.is_(False)).all()
    by_id = {row.id: row for row in rows}
    ordered = [by_id[game_id] for game_id in ranked_ids if game_id in by_id]
    offset = (page - 1) * page_size
    return ordered[offset : offset + page_size]


@router.get("/{game_id}")
def game_profile(
    game_id: int,
    guild_id: int = Query(default=0),
    _: object = Depends(require_permission(PermissionCode.GAMES_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    has_guild_data = _game_has_guild_data(db, guild_id, game_id)
    if not has_guild_data:
        raise HTTPException(status_code=404, detail="Game not found")
    resolved_id = resolve_canonical_game(db, game).id

    automatic = (
        db.query(func.coalesce(func.sum(func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)), 0))
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id, ActivitySession.ended_at.is_not(None))
        .scalar()
    )
    historical = (
        db.query(func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0))
        .join(Game, Game.id == ManualPlaytime.game_id)
        .filter(ManualPlaytime.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id, ManualPlaytime.deleted_at.is_(None))
        .scalar()
    )
    adjustments = (
        db.query(func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0))
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(PlaytimeAdjustment.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id)
        .scalar()
    )
    unique_players = (
        db.query(func.count(func.distinct(ActivitySession.user_id)))
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == resolved_id)
        .scalar()
        or 0
    )

    return {
        "id": resolved_id,
        "display_name": resolve_canonical_game(db, game).display_name,
        "icon_url": game.icon_url,
        "automatic_seconds": int(automatic or 0),
        "historical_seconds": int(historical or 0),
        "adjustment_seconds": int(adjustments or 0),
        "total_seconds": max(0, int((automatic or 0) + (historical or 0) + (adjustments or 0))),
        "unique_players": int(unique_players),
    }


@router.get("/{game_id}/users")
def game_users(
    game_id: int,
    guild_id: int = Query(default=0),
    range_key: str | None = Query(default=None, alias="range"),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(require_permission(PermissionCode.PLAYTIME_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    has_guild_data = _game_has_guild_data(db, guild_id, game_id)
    if not has_guild_data:
        raise HTTPException(status_code=404, detail="Game not found")
    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    resolved_game = resolve_canonical_game(db, game)
    try:
        resolved = resolve_range(range_key, timezone_name=get_settings().timezone, custom_from=from_dt, custom_to=to_dt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return stats_service.ranked_users_for_game(
        db,
        guild_id,
        resolved_game.id,
        limit=100,
        from_dt=resolved.from_dt,
        to_dt=resolved.to_dt,
    )


@router.get("/{game_id}/sessions")
def game_sessions(
    game_id: int,
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(require_permission(PermissionCode.PLAYTIME_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    has_guild_data = _game_has_guild_data(db, guild_id, game_id)
    if not has_guild_data:
        raise HTTPException(status_code=404, detail="Game not found")

    offset = (page - 1) * page_size
    rows = (
        db.query(ActivitySession, User)
        .join(User, User.id == ActivitySession.user_id)
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == game_id)
        .order_by(desc(ActivitySession.started_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return [
        {"session_id": s.id, "user": u.display_name, "started_at": s.started_at, "ended_at": s.ended_at}
        for s, u in rows
    ]


@router.post("/{game_id}/rename")
def rename_game(
    game_id: int,
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    has_guild_data = _game_has_guild_data(db, guild_id, game_id)
    if not has_guild_data:
        raise HTTPException(status_code=404, detail="Game not found")

    old_name = game.display_name
    game.display_name = payload.get("display_name", old_name)
    if old_name != game.display_name:
        add_alias_if_missing(db, game.id, old_name)
    db.commit()
    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_renamed,
        **audit_actor_fields(admin),
        target_user_id=None,
        target_game_id=game.id,
        change_seconds=None,
        reason=f"Renamed from {old_name}",
    )
    return {"ok": True}


@router.get("/{game_id}/aliases")
def list_game_aliases(
    game_id: int,
    guild_id: int = Query(default=0),
    _: object = Depends(require_permission(PermissionCode.GAMES_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game or not _game_has_guild_data(db, guild_id, game_id):
        raise HTTPException(status_code=404, detail="Game not found")

    aliases = db.query(GameAlias).filter(GameAlias.game_id == game_id).order_by(GameAlias.alias.asc()).all()
    return [{"id": a.id, "alias": a.alias} for a in aliases]


@router.post("/{game_id}/aliases")
def add_game_alias(
    game_id: int,
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))
    alias = (payload.get("alias") or "").strip()
    if not alias:
        raise HTTPException(status_code=400, detail="alias is required")

    game = db.query(Game).filter(Game.id == game_id).first()
    if not game or not _game_has_guild_data(db, guild_id, game_id):
        raise HTTPException(status_code=404, detail="Game not found")

    existing = db.query(GameAlias).filter(GameAlias.alias == alias).first()
    if existing and existing.game_id != game_id:
        raise HTTPException(status_code=409, detail="Alias already belongs to another game")
    if existing and existing.game_id == game_id:
        return {"id": existing.id, "alias": existing.alias}

    row = GameAlias(game_id=game_id, alias=alias, normalized_alias=normalize_game_name(alias))
    db.add(row)
    db.commit()
    db.refresh(row)

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_renamed,
        **audit_actor_fields(admin),
        target_user_id=None,
        target_game_id=game_id,
        change_seconds=None,
        reason=f"Alias added: {alias}",
    )
    return {"id": row.id, "alias": row.alias}


@router.post("/merge")
def merge_games(
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))
    source_game_id = int(payload.get("source_game_id") or 0)
    target_game_id = int(payload.get("target_game_id") or 0)
    reason = (payload.get("reason") or "Merged duplicate game").strip()

    if source_game_id <= 0 or target_game_id <= 0 or source_game_id == target_game_id:
        raise HTTPException(status_code=400, detail="source_game_id and target_game_id must be different positive values")

    source = db.query(Game).filter(Game.id == source_game_id).first()
    target = db.query(Game).filter(Game.id == target_game_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target game not found")
    if not _game_has_guild_data(db, guild_id, source_game_id):
        raise HTTPException(status_code=404, detail="Source game not found in guild")

    canonical_source = resolve_canonical_game(db, source)
    canonical_target = resolve_canonical_game(db, target)
    if canonical_source.id == canonical_target.id:
        raise HTTPException(status_code=409, detail="Games already resolve to the same canonical game")

    source.canonical_game_id = canonical_target.id
    source.is_hidden = True
    add_alias_if_missing(db, canonical_target.id, source.display_name)
    for alias in db.query(GameAlias).filter(GameAlias.game_id == source.id).all():
        add_alias_if_missing(db, canonical_target.id, alias.alias)
        alias.game_id = canonical_target.id

    existing_state = (
        db.query(GameMergeSuggestionState)
        .filter(
            GameMergeSuggestionState.source_game_id == source.id,
            GameMergeSuggestionState.target_game_id == canonical_target.id,
        )
        .first()
    )
    if existing_state is None:
        db.add(
            GameMergeSuggestionState(
                source_game_id=source.id,
                target_game_id=canonical_target.id,
                status=MergeSuggestionStatus.accepted,
                decided_by_admin_user_id=admin.admin_user_id,
                decided_by_account_id=admin.account_id,
            )
        )
    else:
        existing_state.status = MergeSuggestionStatus.accepted
        existing_state.decided_by_admin_user_id = admin.admin_user_id
        existing_state.decided_by_account_id = admin.account_id

    db.commit()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_merged,
        **audit_actor_fields(admin),
        target_user_id=None,
        target_game_id=canonical_target.id,
        change_seconds=None,
        reason=reason,
        metadata_json={"source_game_id": source.id, "target_game_id": canonical_target.id},
    )
    return {"ok": True, "source_game_id": source.id, "target_game_id": canonical_target.id}


@router.post("/{game_id}/unmerge")
def unmerge_game(
    game_id: int,
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))
    reason = (payload.get("reason") or "Unmerged game").strip()

    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.canonical_game_id is None:
        raise HTTPException(status_code=409, detail="Game is not currently merged")

    previous_target = game.canonical_game_id
    game.canonical_game_id = None
    game.is_hidden = False
    db.commit()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_unmerged,
        **audit_actor_fields(admin),
        target_user_id=None,
        target_game_id=game.id,
        change_seconds=None,
        reason=reason,
        metadata_json={"previous_target_game_id": previous_target},
    )
    return {"ok": True, "game_id": game.id}


@router.post("/{game_id}/visibility")
def set_game_visibility(
    game_id: int,
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))
    hidden = bool(payload.get("hidden", False))
    reason = (payload.get("reason") or "Visibility updated by admin").strip()

    game = db.query(Game).filter(Game.id == game_id).first()
    if game is None:
        raise HTTPException(status_code=404, detail="Game not found")
    if not _game_has_guild_data(db, guild_id, game_id):
        raise HTTPException(status_code=404, detail="Game not found")
    if not hidden and game.canonical_game_id is not None:
        raise HTTPException(status_code=409, detail="Merged games cannot be set visible directly; unmerge first")

    game.is_hidden = hidden
    db.commit()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_canonical_changed,
        **audit_actor_fields(admin),
        target_user_id=None,
        target_game_id=game.id,
        change_seconds=None,
        reason=reason,
        metadata_json={"is_hidden": bool(game.is_hidden)},
    )
    return {"ok": True, "game_id": game.id, "is_hidden": bool(game.is_hidden)}


@router.get("/meta/merge-suggestions")
def list_merge_suggestions(
    limit: int = Query(default=50, ge=1, le=200),
    confidence: str | None = Query(default=None),
    _: object = Depends(require_permission(PermissionCode.PERMISSIONS_MANAGE)),
    db: Session = Depends(get_db),
):
    rows = suggest_merge_pairs(db, limit=limit)
    if confidence:
        rows = [row for row in rows if row["confidence"] == confidence]
    return rows


@router.get("/meta/catalog")
def list_games_admin_catalog(
    guild_id: int = Query(default=0),
    include_hidden: bool = Query(default=True),
    _: object = Depends(require_permission(PermissionCode.PERMISSIONS_MANAGE)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)

    games_q = db.query(Game)
    if not include_hidden:
        games_q = games_q.filter(Game.is_hidden.is_(False))
    games = games_q.order_by(Game.display_name.asc(), Game.id.asc()).all()

    canonical_names = {row.id: row.display_name for row in db.query(Game.id, Game.display_name).all()}

    return [
        {
            "id": game.id,
            "display_name": game.display_name,
            "normalized_name": game.normalized_name,
            "is_hidden": bool(game.is_hidden),
            "canonical_game_id": game.canonical_game_id,
            "canonical_game_name": canonical_names.get(game.canonical_game_id) if game.canonical_game_id else None,
            "has_guild_data": _game_has_guild_data(db, guild_id, game.id),
        }
        for game in games
    ]


@router.post("/meta/merge-suggestions/{source_game_id}/{target_game_id}/ignore")
def ignore_merge_suggestion(
    source_game_id: int,
    target_game_id: int,
    payload: dict,
    admin=Depends(require_admin),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, int(payload.get("guild_id") or 0))
    if source_game_id == target_game_id:
        raise HTTPException(status_code=400, detail="source and target must differ")

    source = db.query(Game).filter(Game.id == source_game_id).first()
    target = db.query(Game).filter(Game.id == target_game_id).first()
    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Source or target game not found")

    row = (
        db.query(GameMergeSuggestionState)
        .filter(
            GameMergeSuggestionState.source_game_id == source_game_id,
            GameMergeSuggestionState.target_game_id == target_game_id,
        )
        .first()
    )
    if row is None:
        row = GameMergeSuggestionState(
            source_game_id=source_game_id,
            target_game_id=target_game_id,
            status=MergeSuggestionStatus.ignored,
            decided_by_admin_user_id=admin.admin_user_id,
            decided_by_account_id=admin.account_id,
        )
        db.add(row)
    else:
        row.status = MergeSuggestionStatus.ignored
        row.decided_by_admin_user_id = admin.admin_user_id
        row.decided_by_account_id = admin.account_id
    db.commit()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.merge_suggestion_ignored,
        **audit_actor_fields(admin),
        target_user_id=None,
        target_game_id=target_game_id,
        change_seconds=None,
        reason="Merge suggestion ignored",
        metadata_json={"source_game_id": source_game_id, "target_game_id": target_game_id},
    )
    return {"ok": True}
