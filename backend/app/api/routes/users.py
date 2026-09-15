from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import PermissionCode
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.models import ActivitySession, Game, ManualPlaytime, PlaytimeAdjustment, User

router = APIRouter(prefix="/users", tags=["users"])


def _duration_seconds_expr(db: Session):
    if db.bind and db.bind.dialect.name == "sqlite":
        return (func.julianday(ActivitySession.ended_at) - func.julianday(ActivitySession.started_at)) * 86400
    return func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)


@router.get("")
def list_users(
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(require_permission(PermissionCode.USERS_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    offset = (page - 1) * page_size
    rows = (
        db.query(User)
        .filter(User.guild_id == guild_id)
        .order_by(User.display_name.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return rows


@router.get("/{user_id}")
def user_profile(
    user_id: int,
    guild_id: int = Query(default=0),
    _: object = Depends(require_permission(PermissionCode.USERS_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    user = db.query(User).filter(User.id == user_id, User.guild_id == guild_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    automatic = (
        db.query(func.coalesce(func.sum(func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)), 0))
        .filter(ActivitySession.user_id == user.id, ActivitySession.ended_at.is_not(None))
        .scalar()
    )
    historical = (
        db.query(func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0))
        .filter(ManualPlaytime.user_id == user.id, ManualPlaytime.deleted_at.is_(None))
        .scalar()
    )
    adjustment = (
        db.query(func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0))
        .filter(PlaytimeAdjustment.user_id == user.id)
        .scalar()
    )

    return {
        "id": user.id,
        "display_name": user.display_name,
        "username": user.username,
        "avatar_url": user.avatar_url,
        "automatic_seconds": int(automatic or 0),
        "historical_seconds": int(historical or 0),
        "adjustment_seconds": int(adjustment or 0),
        "total_seconds": max(0, int((automatic or 0) + (historical or 0) + (adjustment or 0))),
    }


@router.get("/{user_id}/games")
def user_games(
    user_id: int,
    guild_id: int = Query(default=0),
    _: object = Depends(require_permission(PermissionCode.PLAYTIME_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    user = db.query(User.id).filter(User.id == user_id, User.guild_id == guild_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    auto_q = (
        db.query(
            func.coalesce(Game.canonical_game_id, Game.id).label("game_id"),
            func.coalesce(func.sum(_duration_seconds_expr(db)), 0).label("auto_seconds"),
        )
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.user_id == user_id, ActivitySession.ended_at.is_not(None))
        .group_by(func.coalesce(Game.canonical_game_id, Game.id))
        .subquery()
    )
    hist_q = (
        db.query(
            func.coalesce(Game.canonical_game_id, Game.id).label("game_id"),
            func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0).label("hist_seconds"),
        )
        .join(Game, Game.id == ManualPlaytime.game_id)
        .filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.user_id == user_id, ManualPlaytime.deleted_at.is_(None))
        .group_by(func.coalesce(Game.canonical_game_id, Game.id))
        .subquery()
    )
    adj_q = (
        db.query(
            func.coalesce(Game.canonical_game_id, Game.id).label("game_id"),
            func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0).label("adj_seconds"),
        )
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.user_id == user_id)
        .group_by(func.coalesce(Game.canonical_game_id, Game.id))
        .subquery()
    )

    rows = (
        db.query(
            Game.id,
            Game.display_name,
            (
                func.coalesce(auto_q.c.auto_seconds, 0)
                + func.coalesce(hist_q.c.hist_seconds, 0)
                + func.coalesce(adj_q.c.adj_seconds, 0)
            ).label("seconds"),
        )
        .join(auto_q, auto_q.c.game_id == Game.id, isouter=True)
        .join(hist_q, hist_q.c.game_id == Game.id, isouter=True)
        .join(adj_q, adj_q.c.game_id == Game.id, isouter=True)
        .filter((auto_q.c.game_id.is_not(None)) | (hist_q.c.game_id.is_not(None)) | (adj_q.c.game_id.is_not(None)))
        .order_by(desc("seconds"))
        .all()
    )
    return [{"id": r[0], "name": r[1], "total_seconds": max(0, int(r[2] or 0))} for r in rows]


@router.get("/{user_id}/sessions")
def user_sessions(
    user_id: int,
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(require_permission(PermissionCode.PLAYTIME_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    user = db.query(User.id).filter(User.id == user_id, User.guild_id == guild_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    offset = (page - 1) * page_size
    rows = (
        db.query(ActivitySession, Game)
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.user_id == user_id, ActivitySession.guild_id == guild_id)
        .order_by(desc(ActivitySession.started_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return [
        {
            "session_id": s.id,
            "game": g.display_name,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
        }
        for s, g in rows
    ]


@router.delete("/{user_id}")
def delete_user(
    user_id: int,
    guild_id: int = Query(default=0),
    _=Depends(require_permission(PermissionCode.USERS_MANAGE)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    user = db.query(User).filter(User.id == user_id, User.guild_id == guild_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"ok": True, "deleted_user_id": user_id}
