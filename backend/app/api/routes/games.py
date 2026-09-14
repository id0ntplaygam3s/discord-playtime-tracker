from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.models import ActivitySession, AuditAction, Game, GameAlias, ManualPlaytime, PlaytimeAdjustment, User
from app.services.session_service import write_audit_log
from app.services.normalization import normalize_game_name

router = APIRouter(prefix="/games", tags=["games"])


def _duration_seconds_expr(db: Session):
    if db.bind and db.bind.dialect.name == "sqlite":
        return (func.julianday(ActivitySession.ended_at) - func.julianday(ActivitySession.started_at)) * 86400
    return func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)


def _game_has_guild_data(db: Session, guild_id: int, game_id: int) -> bool:
    return bool(
        db.query(ActivitySession.id).filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == game_id).first()
        or db.query(ManualPlaytime.id).filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.game_id == game_id).first()
        or db.query(PlaytimeAdjustment.id)
        .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.game_id == game_id)
        .first()
    )


@router.get("")
def list_games(
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    offset = (page - 1) * page_size
    rows = (
        db.query(Game)
        .filter(
            Game.is_hidden.is_(False),
            (db.query(ActivitySession.id).filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == Game.id).exists())
            | (db.query(ManualPlaytime.id).filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.game_id == Game.id).exists())
            | (
                db.query(PlaytimeAdjustment.id)
                .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.game_id == Game.id)
                .exists()
            )
        )
        .order_by(Game.display_name.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return rows


@router.get("/{game_id}")
def game_profile(
    game_id: int,
    guild_id: int = Query(default=0),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    has_guild_data = _game_has_guild_data(db, guild_id, game_id)
    if not has_guild_data:
        raise HTTPException(status_code=404, detail="Game not found")

    automatic = (
        db.query(func.coalesce(func.sum(func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)), 0))
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == game.id, ActivitySession.ended_at.is_not(None))
        .scalar()
    )
    historical = (
        db.query(func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0))
        .filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.game_id == game.id, ManualPlaytime.deleted_at.is_(None))
        .scalar()
    )
    adjustments = (
        db.query(func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0))
        .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.game_id == game.id)
        .scalar()
    )
    unique_players = (
        db.query(func.count(func.distinct(ActivitySession.user_id)))
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == game.id)
        .scalar()
        or 0
    )

    return {
        "id": game.id,
        "display_name": game.display_name,
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
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    has_guild_data = _game_has_guild_data(db, guild_id, game_id)
    if not has_guild_data:
        raise HTTPException(status_code=404, detail="Game not found")

    auto_q = (
        db.query(
            ActivitySession.user_id.label("user_id"),
            func.coalesce(func.sum(_duration_seconds_expr(db)), 0).label("auto_seconds"),
        )
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == game_id, ActivitySession.ended_at.is_not(None))
        .group_by(ActivitySession.user_id)
        .subquery()
    )
    hist_q = (
        db.query(
            ManualPlaytime.user_id.label("user_id"),
            func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0).label("hist_seconds"),
        )
        .filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.game_id == game_id, ManualPlaytime.deleted_at.is_(None))
        .group_by(ManualPlaytime.user_id)
        .subquery()
    )
    adj_q = (
        db.query(
            PlaytimeAdjustment.user_id.label("user_id"),
            func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0).label("adj_seconds"),
        )
        .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.game_id == game_id)
        .group_by(PlaytimeAdjustment.user_id)
        .subquery()
    )

    rows = (
        db.query(
            User.id,
            User.display_name,
            (
                func.coalesce(auto_q.c.auto_seconds, 0)
                + func.coalesce(hist_q.c.hist_seconds, 0)
                + func.coalesce(adj_q.c.adj_seconds, 0)
            ).label("seconds"),
        )
        .join(auto_q, auto_q.c.user_id == User.id, isouter=True)
        .join(hist_q, hist_q.c.user_id == User.id, isouter=True)
        .join(adj_q, adj_q.c.user_id == User.id, isouter=True)
        .filter(User.guild_id == guild_id, (auto_q.c.user_id.is_not(None)) | (hist_q.c.user_id.is_not(None)) | (adj_q.c.user_id.is_not(None)))
        .order_by(desc("seconds"))
        .all()
    )
    return [{"id": r[0], "name": r[1], "total_seconds": max(0, int(r[2] or 0))} for r in rows]


@router.get("/{game_id}/sessions")
def game_sessions(
    game_id: int,
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(get_current_user),
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
    db.commit()
    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_renamed,
        admin_user_id=admin.id,
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
    _: object = Depends(get_current_user),
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

    row = GameAlias(game_id=game_id, alias=alias)
    db.add(row)
    db.commit()
    db.refresh(row)

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_renamed,
        admin_user_id=admin.id,
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

    if source.display_name != target.display_name:
        existing_alias = db.query(GameAlias).filter(GameAlias.alias == source.display_name).first()
        if existing_alias is None:
            db.add(GameAlias(game_id=target_game_id, alias=source.display_name))

    for alias in db.query(GameAlias).filter(GameAlias.game_id == source_game_id).all():
        conflict = db.query(GameAlias).filter(GameAlias.alias == alias.alias).first()
        if conflict is None or conflict.game_id == source_game_id:
            alias.game_id = target_game_id

    db.query(ActivitySession).filter(ActivitySession.guild_id == guild_id, ActivitySession.game_id == source_game_id).update(
        {ActivitySession.game_id: target_game_id}, synchronize_session=False
    )
    db.query(ManualPlaytime).filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.game_id == source_game_id).update(
        {ManualPlaytime.game_id: target_game_id}, synchronize_session=False
    )
    db.query(PlaytimeAdjustment).filter(
        PlaytimeAdjustment.guild_id == guild_id,
        PlaytimeAdjustment.game_id == source_game_id,
    ).update({PlaytimeAdjustment.game_id: target_game_id}, synchronize_session=False)

    source.is_hidden = True
    source.display_name = f"Merged into {target.display_name}"
    source.normalized_name = normalize_game_name(f"merged-source-{source.id}-{source.normalized_name}")

    db.commit()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.game_merged,
        admin_user_id=admin.id,
        target_user_id=None,
        target_game_id=target_game_id,
        change_seconds=None,
        reason=reason,
        metadata_json={"source_game_id": source_game_id, "target_game_id": target_game_id},
    )
    return {"ok": True, "source_game_id": source_game_id, "target_game_id": target_game_id}
