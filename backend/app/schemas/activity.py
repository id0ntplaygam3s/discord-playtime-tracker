from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ActiveSessionItem(BaseModel):
    session_id: int
    user_id: int
    user_name: str
    avatar_url: str | None
    game_id: int
    game_name: str
    started_at: datetime


class RecentActivityItem(BaseModel):
    event: str
    user_name: str
    game_name: str | None
    happened_at: datetime
