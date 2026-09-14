from __future__ import annotations

from pydantic import BaseModel, Field

from app.models import ManualSource


class ManualPlaytimeCreate(BaseModel):
    guild_id: int
    user_id: int
    game_id: int | None = None
    custom_game_title: str | None = None
    hours: int = Field(ge=0, default=0)
    minutes: int = Field(ge=0, le=59, default=0)
    source: ManualSource
    note: str | None = None


class AdjustmentCreate(BaseModel):
    guild_id: int
    user_id: int
    game_id: int
    hours: int = 0
    minutes: int = 0
    sign: int = Field(default=1)
    reason: str


class SetAbsoluteTotalRequest(BaseModel):
    guild_id: int
    user_id: int
    game_id: int
    desired_total_seconds: int = Field(gt=0)
    reason: str


class SteamImportPreviewRequest(BaseModel):
    guild_id: int
    user_id: int
    steam_profile: str


class SteamPreviewGame(BaseModel):
    appid: int
    name: str
    playtime_minutes: int
    duration_seconds: int


class SteamImportPreviewResponse(BaseModel):
    steam_id: str
    profile_label: str
    total_games: int
    games: list[SteamPreviewGame]


class SteamImportRequest(BaseModel):
    guild_id: int
    user_id: int
    steam_profile: str
    replace_previous: bool = True
    max_games: int = Field(default=200, ge=1, le=500)


class SteamImportResponse(BaseModel):
    imported: int
    replaced: int
    steam_id: str
