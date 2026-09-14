from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_combined_seconds: int
    total_automatic_seconds: int
    total_historical_seconds: int
    total_adjustment_seconds: int
    tracked_users: int
    games: int
    currently_playing: int
    most_played_game: str | None
    most_active_user: str | None


class RankedPlaytime(BaseModel):
    id: int
    name: str
    total_seconds: int


class TimeBucketPoint(BaseModel):
    bucket: datetime
    total_seconds: int
