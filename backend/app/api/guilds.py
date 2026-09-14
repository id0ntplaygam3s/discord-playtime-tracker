from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Guild


def resolve_guild_id(db: Session, requested_guild_id: int | None) -> int:
    if requested_guild_id and requested_guild_id > 0:
        return requested_guild_id

    settings = get_settings()
    guild = None
    if settings.discord_guild_id:
        guild = db.query(Guild.id).filter(Guild.discord_guild_id == settings.discord_guild_id).first()
    if guild is None:
        guild = db.query(Guild.id).order_by(Guild.id.asc()).first()
    if not guild:
        raise HTTPException(status_code=400, detail="Configured Discord guild has not been initialized yet")
    return int(guild[0])
