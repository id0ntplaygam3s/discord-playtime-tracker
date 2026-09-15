from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import ActivitySession, Game, ManualPlaytime, PlaytimeAdjustment, User

DataSource = Literal["combined", "automatic", "historical", "adjustments"]


def _automatic_duration_expr(db: Session, now_dt: datetime, from_dt: datetime | None = None, to_dt: datetime | None = None):
    end_expr = func.coalesce(ActivitySession.ended_at, now_dt)
    start_expr = ActivitySession.started_at

    if db.bind and db.bind.dialect.name == "sqlite":
        if from_dt is not None:
            start_expr = func.max(start_expr, from_dt)
        if to_dt is not None:
            end_expr = func.min(end_expr, to_dt)
        return (func.julianday(end_expr) - func.julianday(start_expr)) * 86400

    if from_dt is not None:
        start_expr = func.greatest(start_expr, from_dt)
    if to_dt is not None:
        end_expr = func.least(end_expr, to_dt)
    return func.extract("epoch", end_expr - start_expr)


def _automatic_overlap_filters(now_dt: datetime, from_dt: datetime | None = None, to_dt: datetime | None = None):
    filters = []
    if from_dt is not None:
        filters.append(func.coalesce(ActivitySession.ended_at, now_dt) > from_dt)
    if to_dt is not None:
        filters.append(ActivitySession.started_at < to_dt)
    return filters


def _source_sums(db: Session, guild_id: int, from_dt: datetime | None = None, to_dt: datetime | None = None):
    now_dt = datetime.now(timezone.utc)
    automatic = (
        db.query(func.coalesce(func.sum(_automatic_duration_expr(db, now_dt, from_dt, to_dt)), 0))
        .filter(ActivitySession.guild_id == guild_id, *_automatic_overlap_filters(now_dt, from_dt, to_dt))
        .scalar()
    )

    hist_filters = [ManualPlaytime.guild_id == guild_id, ManualPlaytime.deleted_at.is_(None)]
    if from_dt is not None:
        hist_filters.append(ManualPlaytime.created_at >= from_dt)
    if to_dt is not None:
        hist_filters.append(ManualPlaytime.created_at < to_dt)
    historical = db.query(func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0)).filter(*hist_filters).scalar()

    adj_filters = [PlaytimeAdjustment.guild_id == guild_id]
    if from_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at >= from_dt)
    if to_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at < to_dt)
    adjustments = db.query(func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0)).filter(*adj_filters).scalar()

    return int(automatic or 0), int(historical or 0), int(adjustments or 0)


def get_overview(db: Session, guild_id: int, from_dt: datetime | None = None, to_dt: datetime | None = None) -> dict:
    automatic, historical, adjustments = _source_sums(db, guild_id, from_dt=from_dt, to_dt=to_dt)

    tracked_users = db.query(func.count(User.id)).filter(User.guild_id == guild_id, User.is_hidden.is_(False)).scalar() or 0
    games = len(ranked_games(db, guild_id, source="combined", limit=5000, from_dt=from_dt, to_dt=to_dt))
    currently_playing = (
        db.query(func.count(ActivitySession.id))
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.ended_at.is_(None))
        .scalar()
        or 0
    )

    top_games = ranked_games(db, guild_id, source="combined", limit=1, from_dt=from_dt, to_dt=to_dt)
    top_users = ranked_users(db, guild_id, source="combined", limit=1, from_dt=from_dt, to_dt=to_dt)

    return {
        "total_combined_seconds": max(0, automatic + historical + adjustments),
        "total_automatic_seconds": automatic,
        "total_historical_seconds": historical,
        "total_adjustment_seconds": adjustments,
        "tracked_users": int(tracked_users),
        "games": int(games),
        "currently_playing": int(currently_playing),
        "most_played_game": top_games[0]["name"] if top_games else None,
        "most_active_user": top_users[0]["name"] if top_users else None,
    }


def ranked_games(
    db: Session,
    guild_id: int,
    source: DataSource = "combined",
    limit: int = 20,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[dict]:
    now_dt = datetime.now(timezone.utc)
    auto_q = (
        db.query(
            func.coalesce(Game.canonical_game_id, Game.id).label("game_id"),
            func.coalesce(func.sum(_automatic_duration_expr(db, now_dt, from_dt, to_dt)), 0).label("auto_seconds"),
        )
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(ActivitySession.guild_id == guild_id, *_automatic_overlap_filters(now_dt, from_dt, to_dt))
        .group_by(func.coalesce(Game.canonical_game_id, Game.id))
        .subquery()
    )

    hist_filters = [ManualPlaytime.guild_id == guild_id, ManualPlaytime.deleted_at.is_(None)]
    if from_dt is not None:
        hist_filters.append(ManualPlaytime.created_at >= from_dt)
    if to_dt is not None:
        hist_filters.append(ManualPlaytime.created_at < to_dt)
    hist_q = (
        db.query(
            func.coalesce(Game.canonical_game_id, Game.id).label("game_id"),
            func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0).label("hist_seconds"),
        )
        .join(Game, Game.id == ManualPlaytime.game_id)
        .filter(*hist_filters)
        .group_by(func.coalesce(Game.canonical_game_id, Game.id))
        .subquery()
    )

    adj_filters = [PlaytimeAdjustment.guild_id == guild_id]
    if from_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at >= from_dt)
    if to_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at < to_dt)
    adj_q = (
        db.query(
            func.coalesce(Game.canonical_game_id, Game.id).label("game_id"),
            func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0).label("adj_seconds"),
        )
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(*adj_filters)
        .group_by(func.coalesce(Game.canonical_game_id, Game.id))
        .subquery()
    )

    total_expr = func.coalesce(auto_q.c.auto_seconds, 0) + func.coalesce(hist_q.c.hist_seconds, 0) + func.coalesce(adj_q.c.adj_seconds, 0)
    if source == "automatic":
        total_expr = func.coalesce(auto_q.c.auto_seconds, 0)
    elif source == "historical":
        total_expr = func.coalesce(hist_q.c.hist_seconds, 0)
    elif source == "adjustments":
        total_expr = func.coalesce(adj_q.c.adj_seconds, 0)

    rows = (
        db.query(Game.id, Game.display_name, total_expr.label("seconds"))
        .join(auto_q, auto_q.c.game_id == Game.id, isouter=True)
        .join(hist_q, hist_q.c.game_id == Game.id, isouter=True)
        .join(adj_q, adj_q.c.game_id == Game.id, isouter=True)
        .filter(Game.is_hidden.is_(False), (auto_q.c.game_id.is_not(None)) | (hist_q.c.game_id.is_not(None)) | (adj_q.c.game_id.is_not(None)))
        .order_by(text("seconds DESC"))
        .limit(limit)
        .all()
    )
    return [{"id": int(r[0]), "name": r[1], "total_seconds": max(0, int(r[2] or 0))} for r in rows]


def ranked_users(
    db: Session,
    guild_id: int,
    source: DataSource = "combined",
    limit: int = 20,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[dict]:
    now_dt = datetime.now(timezone.utc)
    auto_q = (
        db.query(
            ActivitySession.user_id.label("user_id"),
            func.coalesce(func.sum(_automatic_duration_expr(db, now_dt, from_dt, to_dt)), 0).label("auto_seconds"),
        )
        .filter(ActivitySession.guild_id == guild_id, *_automatic_overlap_filters(now_dt, from_dt, to_dt))
        .group_by(ActivitySession.user_id)
        .subquery()
    )

    hist_filters = [ManualPlaytime.guild_id == guild_id, ManualPlaytime.deleted_at.is_(None)]
    if from_dt is not None:
        hist_filters.append(ManualPlaytime.created_at >= from_dt)
    if to_dt is not None:
        hist_filters.append(ManualPlaytime.created_at < to_dt)
    hist_q = (
        db.query(
            ManualPlaytime.user_id.label("user_id"),
            func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0).label("hist_seconds"),
        )
        .filter(*hist_filters)
        .group_by(ManualPlaytime.user_id)
        .subquery()
    )

    adj_filters = [PlaytimeAdjustment.guild_id == guild_id]
    if from_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at >= from_dt)
    if to_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at < to_dt)
    adj_q = (
        db.query(
            PlaytimeAdjustment.user_id.label("user_id"),
            func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0).label("adj_seconds"),
        )
        .filter(*adj_filters)
        .group_by(PlaytimeAdjustment.user_id)
        .subquery()
    )

    total_expr = func.coalesce(auto_q.c.auto_seconds, 0) + func.coalesce(hist_q.c.hist_seconds, 0) + func.coalesce(adj_q.c.adj_seconds, 0)
    if source == "automatic":
        total_expr = func.coalesce(auto_q.c.auto_seconds, 0)
    elif source == "historical":
        total_expr = func.coalesce(hist_q.c.hist_seconds, 0)
    elif source == "adjustments":
        total_expr = func.coalesce(adj_q.c.adj_seconds, 0)

    rows = (
        db.query(User.id, User.display_name, total_expr.label("seconds"))
        .join(auto_q, auto_q.c.user_id == User.id, isouter=True)
        .join(hist_q, hist_q.c.user_id == User.id, isouter=True)
        .join(adj_q, adj_q.c.user_id == User.id, isouter=True)
        .filter(
            User.guild_id == guild_id,
            User.is_hidden.is_(False),
            (auto_q.c.user_id.is_not(None)) | (hist_q.c.user_id.is_not(None)) | (adj_q.c.user_id.is_not(None)),
        )
        .order_by(text("seconds DESC"))
        .limit(limit)
        .all()
    )
    return [{"id": int(r[0]), "name": r[1], "total_seconds": max(0, int(r[2] or 0))} for r in rows]


def ranked_users_for_game(
    db: Session,
    guild_id: int,
    game_id: int,
    *,
    limit: int = 20,
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[dict]:
    now_dt = datetime.now(timezone.utc)
    auto_q = (
        db.query(
            ActivitySession.user_id.label("user_id"),
            func.coalesce(func.sum(_automatic_duration_expr(db, now_dt, from_dt, to_dt)), 0).label("auto_seconds"),
        )
        .join(Game, Game.id == ActivitySession.game_id)
        .filter(
            ActivitySession.guild_id == guild_id,
            func.coalesce(Game.canonical_game_id, Game.id) == game_id,
            *_automatic_overlap_filters(now_dt, from_dt, to_dt),
        )
        .group_by(ActivitySession.user_id)
        .subquery()
    )

    hist_filters = [
        ManualPlaytime.guild_id == guild_id,
        ManualPlaytime.deleted_at.is_(None),
        func.coalesce(Game.canonical_game_id, Game.id) == game_id,
    ]
    if from_dt is not None:
        hist_filters.append(ManualPlaytime.created_at >= from_dt)
    if to_dt is not None:
        hist_filters.append(ManualPlaytime.created_at < to_dt)
    hist_q = (
        db.query(
            ManualPlaytime.user_id.label("user_id"),
            func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0).label("hist_seconds"),
        )
        .join(Game, Game.id == ManualPlaytime.game_id)
        .filter(*hist_filters)
        .group_by(ManualPlaytime.user_id)
        .subquery()
    )

    adj_filters = [PlaytimeAdjustment.guild_id == guild_id, func.coalesce(Game.canonical_game_id, Game.id) == game_id]
    if from_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at >= from_dt)
    if to_dt is not None:
        adj_filters.append(PlaytimeAdjustment.created_at < to_dt)
    adj_q = (
        db.query(
            PlaytimeAdjustment.user_id.label("user_id"),
            func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0).label("adj_seconds"),
        )
        .join(Game, Game.id == PlaytimeAdjustment.game_id)
        .filter(*adj_filters)
        .group_by(PlaytimeAdjustment.user_id)
        .subquery()
    )

    rows = (
        db.query(
            User.id,
            User.display_name,
            (
                func.coalesce(auto_q.c.auto_seconds, 0)
                + func.coalesce(hist_q.c.hist_seconds, 0)
                + func.coalesce(adj_q.c.adj_seconds, 0)
            ).label("seconds"),
        )
        .join(auto_q, auto_q.c.user_id == User.id, isouter=True)
        .join(hist_q, hist_q.c.user_id == User.id, isouter=True)
        .join(adj_q, adj_q.c.user_id == User.id, isouter=True)
        .filter(
            User.guild_id == guild_id,
            (auto_q.c.user_id.is_not(None)) | (hist_q.c.user_id.is_not(None)) | (adj_q.c.user_id.is_not(None)),
        )
        .order_by(text("seconds DESC"))
        .limit(limit)
        .all()
    )
    return [{"id": int(r[0]), "name": r[1], "total_seconds": max(0, int(r[2] or 0))} for r in rows]


def activity_over_time(
    db: Session,
    guild_id: int,
    granularity: Literal["daily", "weekly", "monthly"] = "daily",
    from_dt: datetime | None = None,
    to_dt: datetime | None = None,
) -> list[dict]:
    settings = get_settings()
    token = "day"
    if granularity == "weekly":
        token = "week"
    elif granularity == "monthly":
        token = "month"

    query = text(
        """
        SELECT
          (date_trunc(:g, bucket_local) AT TIME ZONE :tz) AS bucket,
          SUM(seconds)::bigint AS total_seconds
        FROM (
          SELECT
            gs AS bucket_local,
            EXTRACT(
              EPOCH FROM LEAST(timezone(:tz, COALESCE(s.ended_at, NOW())), gs + interval '1 day')
              - GREATEST(timezone(:tz, s.started_at), gs)
            ) AS seconds
          FROM activity_sessions s
          JOIN LATERAL generate_series(
            date_trunc('day', timezone(:tz, s.started_at)),
            date_trunc('day', timezone(:tz, COALESCE(s.ended_at, NOW()))),
            interval '1 day'
          ) AS gs ON true
          WHERE s.guild_id = :guild_id
            AND (s.ended_at IS NULL OR s.ended_at >= s.started_at)
                        AND (CAST(:from_dt AS timestamptz) IS NULL OR COALESCE(s.ended_at, NOW()) > CAST(:from_dt AS timestamptz))
                        AND (CAST(:to_dt AS timestamptz) IS NULL OR s.started_at < CAST(:to_dt AS timestamptz))
        ) split
        GROUP BY (date_trunc(:g, bucket_local) AT TIME ZONE :tz)
        ORDER BY bucket ASC
        """
    )
    rows = db.execute(
        query,
        {
            "guild_id": guild_id,
            "g": token,
            "tz": settings.timezone,
            "from_dt": from_dt,
            "to_dt": to_dt,
        },
    ).fetchall()

    return [{"bucket": r[0], "total_seconds": max(0, int(r[1] or 0))} for r in rows]
