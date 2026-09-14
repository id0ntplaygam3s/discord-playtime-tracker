from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SystemStatus(BaseModel):
    status: str
    discord_status: str
    database_status: str
    bot_uptime_seconds: int | None
    last_discord_event_at: datetime | None
    last_database_write_at: datetime | None
    active_sessions: int
    app_version: str
