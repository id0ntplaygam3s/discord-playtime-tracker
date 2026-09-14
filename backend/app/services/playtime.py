from __future__ import annotations

from datetime import timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import ActivitySession, ManualPlaytime, PlaytimeAdjustment


def total_seconds_for_user_game(db: Session, guild_id: int, user_id: int, game_id: int) -> int:
    automatic_sessions = (
        db.query(ActivitySession.started_at, ActivitySession.ended_at)
        .filter(
            ActivitySession.guild_id == guild_id,
            ActivitySession.user_id == user_id,
            ActivitySession.game_id == game_id,
            ActivitySession.ended_at.is_not(None),
        )
        .all()
    )
    automatic = 0
    for started_at, ended_at in automatic_sessions:
        if ended_at is None:
            continue
        start = started_at.astimezone(timezone.utc) if started_at.tzinfo else started_at.replace(tzinfo=timezone.utc)
        end = ended_at.astimezone(timezone.utc) if ended_at.tzinfo else ended_at.replace(tzinfo=timezone.utc)
        automatic += max(0, int((end - start).total_seconds()))
    historical = (
        db.query(func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0))
        .filter(
            ManualPlaytime.guild_id == guild_id,
            ManualPlaytime.user_id == user_id,
            ManualPlaytime.game_id == game_id,
            ManualPlaytime.deleted_at.is_(None),
        )
        .scalar()
    )
    adjustments = (
        db.query(func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0))
        .filter(
            PlaytimeAdjustment.guild_id == guild_id,
            PlaytimeAdjustment.user_id == user_id,
            PlaytimeAdjustment.game_id == game_id,
        )
        .scalar()
    )
    return int(automatic or 0) + int(historical or 0) + int(adjustments or 0)
