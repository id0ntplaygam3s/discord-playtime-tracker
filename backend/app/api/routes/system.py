from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import ActivitySession, Guild, ManualPlaytime, PlaytimeAdjustment
from app.schemas.system import SystemStatus

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/status", response_model=SystemStatus)
def system_status(request: Request, _: object = Depends(get_current_user), db: Session = Depends(get_db)):
    settings = get_settings()
    manager = request.app.state.bot_manager
    guild = db.query(Guild).filter(Guild.discord_guild_id == settings.discord_guild_id).first()
    guild_id = guild.id if guild else None

    active_sessions = 0
    if guild_id is not None:
        active_sessions = (
            db.query(ActivitySession)
            .filter(ActivitySession.guild_id == guild_id, ActivitySession.ended_at.is_(None))
            .count()
        )
    uptime = None
    if manager.started_at:
        uptime = int((datetime.now(timezone.utc) - manager.started_at).total_seconds())

    db_online = True
    try:
        db.execute(select(func.now()))
    except Exception:
        db_online = False

    last_session_write = None
    last_manual_write = None
    last_adjustment_write = None
    if guild_id is not None:
        last_session_write = db.query(func.max(ActivitySession.updated_at)).filter(ActivitySession.guild_id == guild_id).scalar()
        last_manual_write = db.query(func.max(ManualPlaytime.updated_at)).filter(ManualPlaytime.guild_id == guild_id).scalar()
        last_adjustment_write = db.query(func.max(PlaytimeAdjustment.created_at)).filter(PlaytimeAdjustment.guild_id == guild_id).scalar()
    last_database_write = max(
        [dt for dt in [last_session_write, last_manual_write, last_adjustment_write] if dt is not None],
        default=None,
    )

    status = "healthy" if manager.connected and db_online else "degraded"
    return SystemStatus(
        status=status,
        discord_status="online" if manager.connected else "offline",
        database_status="online" if db_online else "offline",
        bot_uptime_seconds=uptime,
        last_discord_event_at=manager.last_event_at,
        last_database_write_at=last_database_write,
        active_sessions=active_sessions,
        app_version=settings.app_version,
    )
