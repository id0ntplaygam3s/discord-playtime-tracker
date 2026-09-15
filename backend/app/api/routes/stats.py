from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core.permissions import PermissionCode
from app.core.config import get_settings
from app.api.guilds import resolve_guild_id
from app.db.session import get_db
from app.schemas.stats import OverviewStats, RankedPlaytime, TimeBucketPoint
from app.services.date_ranges import resolve_range
from app.services import stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


def _resolve_range_or_400(range_key: str | None, timezone_name: str, from_dt: datetime | None, to_dt: datetime | None):
    try:
        return resolve_range(range_key, timezone_name=timezone_name, custom_from=from_dt, custom_to=to_dt)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/overview", response_model=OverviewStats)
def overview(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    range_key: str | None = Query(default=None, alias="range"),
    _: object = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    return stats_service.get_overview(db, guild_id, from_dt=resolved.from_dt, to_dt=resolved.to_dt)


@router.get("/games", response_model=list[RankedPlaytime])
def games(
    guild_id: int = Query(default=0),
    source: Literal["combined", "automatic", "historical", "adjustments"] = "combined",
    limit: int = Query(default=20, ge=1, le=5000),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    range_key: str | None = Query(default=None, alias="range"),
    _: object = Depends(require_permission(PermissionCode.GAMES_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    return stats_service.ranked_games(
        db,
        guild_id,
        source=source,
        limit=limit,
        from_dt=resolved.from_dt,
        to_dt=resolved.to_dt,
    )


@router.get("/users", response_model=list[RankedPlaytime])
def users(
    guild_id: int = Query(default=0),
    source: Literal["combined", "automatic", "historical", "adjustments"] = "combined",
    limit: int = Query(default=20, ge=1, le=5000),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    range_key: str | None = Query(default=None, alias="range"),
    _: object = Depends(require_permission(PermissionCode.USERS_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    return stats_service.ranked_users(
        db,
        guild_id,
        source=source,
        limit=limit,
        from_dt=resolved.from_dt,
        to_dt=resolved.to_dt,
    )


@router.get("/daily", response_model=list[TimeBucketPoint])
def daily(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    range_key: str | None = Query(default=None, alias="range"),
    _: object = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    return stats_service.activity_over_time(db, guild_id, "daily", from_dt=resolved.from_dt, to_dt=resolved.to_dt)


@router.get("/weekly", response_model=list[TimeBucketPoint])
def weekly(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    range_key: str | None = Query(default=None, alias="range"),
    _: object = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    return stats_service.activity_over_time(db, guild_id, "weekly", from_dt=resolved.from_dt, to_dt=resolved.to_dt)


@router.get("/monthly", response_model=list[TimeBucketPoint])
def monthly(
    guild_id: int = Query(default=0),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    range_key: str | None = Query(default=None, alias="range"),
    _: object = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    return stats_service.activity_over_time(db, guild_id, "monthly", from_dt=resolved.from_dt, to_dt=resolved.to_dt)


@router.get("/activity-over-time", response_model=list[TimeBucketPoint])
def activity_over_time(
    guild_id: int = Query(default=0),
    range_key: str = Query(default="30d", alias="range"),
    from_dt: datetime | None = Query(default=None, alias="from"),
    to_dt: datetime | None = Query(default=None, alias="to"),
    _: object = Depends(require_permission(PermissionCode.DASHBOARD_VIEW)),
    db: Session = Depends(get_db),
):
    guild_id = resolve_guild_id(db, guild_id)
    resolved = _resolve_range_or_400(range_key, get_settings().timezone, from_dt, to_dt)
    key = resolved.key
    granularity: Literal["daily", "weekly", "monthly"] = "daily"
    if key in {"180d", "365d", "all", "ytd"}:
        granularity = "weekly"
    if key == "all":
        granularity = "monthly"
    return stats_service.activity_over_time(
        db,
        guild_id,
        granularity,
        from_dt=resolved.from_dt,
        to_dt=resolved.to_dt,
    )
