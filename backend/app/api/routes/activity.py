from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.models import ActivitySession, Game, User
from app.schemas.activity import ActiveSessionItem, RecentActivityItem

router = APIRouter(prefix="/activity", tags=["activity"])


@router.get("/active", response_model=list[ActiveSessionItem])
def active_sessions(
    guild_id: int = Query(default=0),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    rows = (
        db.query(ActivitySession, User, Game)
        .join(User, User.id == ActivitySession.user_id)
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.ended_at.is_(None))
        .order_by(ActivitySession.started_at.asc())
        .all()
    )
    return [
        ActiveSessionItem(
            session_id=s.id,
            user_id=u.id,
            user_name=u.display_name,
            avatar_url=u.avatar_url,
            game_id=g.id,
            game_name=g.display_name,
            started_at=s.started_at,
        )
        for s, u, g in rows
    ]


@router.get("/recent", response_model=list[RecentActivityItem])
def recent_activity(
    guild_id: int = Query(default=0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    offset = (page - 1) * page_size
    rows = (
        db.query(ActivitySession, User, Game)
        .join(User, User.id == ActivitySession.user_id)
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id)
        .order_by(desc(ActivitySession.updated_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    result: list[RecentActivityItem] = []
    for session, user, game in rows:
        if session.ended_at is None:
            result.append(RecentActivityItem(event="started", user_name=user.display_name, game_name=game.display_name, happened_at=session.started_at))
        else:
            result.append(RecentActivityItem(event="stopped", user_name=user.display_name, game_name=game.display_name, happened_at=session.ended_at))
    return result
