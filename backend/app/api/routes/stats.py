from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.schemas.stats import OverviewStats, RankedPlaytime, TimeBucketPoint
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=OverviewStats)
def overview(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    return stats_service.get_overview(db, guild_id, from_dt=from_dt, to_dt=to_dt)


@router.get("/games", response_model=list[RankedPlaytime])
def games(
    guild_id: int = Query(default=0),
    source: Literal["combined", "automatic", "historical", "adjustments"] = "combined",
    limit: int = Query(default=20, ge=1, le=100),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    return stats_service.ranked_games(db, guild_id, source=source, limit=limit, from_dt=from_dt, to_dt=to_dt)


@router.get("/users", response_model=list[RankedPlaytime])
def users(
    guild_id: int = Query(default=0),
    source: Literal["combined", "automatic", "historical", "adjustments"] = "combined",
    limit: int = Query(default=20, ge=1, le=100),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    return stats_service.ranked_users(db, guild_id, source=source, limit=limit, from_dt=from_dt, to_dt=to_dt)


@router.get("/daily", response_model=list[TimeBucketPoint])
def daily(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    return stats_service.activity_over_time(db, guild_id, "daily", from_dt=from_dt, to_dt=to_dt)


@router.get("/weekly", response_model=list[TimeBucketPoint])
def weekly(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    return stats_service.activity_over_time(db, guild_id, "weekly", from_dt=from_dt, to_dt=to_dt)


@router.get("/monthly", response_model=list[TimeBucketPoint])
def monthly(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    return stats_service.activity_over_time(db, guild_id, "monthly", from_dt=from_dt, to_dt=to_dt)
