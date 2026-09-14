from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import ActivitySession, Game, ManualPlaytime, PlaytimeAdjustment, User

router = APIRouter(prefix="/compare", tags=["compare"])


def _per_user_game_totals(db: Session, guild_id: int, user_ids: list[int]):
    users = {
        row[0]: row[1]
        for row in db.query(User.id, User.display_name)
        .filter(User.guild_id == guild_id, User.id.in_(user_ids), User.is_hidden.is_(False))
        .all()
    }
    games = {row[0]: row[1] for row in db.query(Game.id, Game.display_name).filter(Game.is_hidden.is_(False)).all()}

    totals: dict[tuple[int, int], int] = {}

    auto_rows = (
        db.query(
            ActivitySession.user_id,
            ActivitySession.game_id,
            func.coalesce(func.sum(func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)), 0),
        )
        .filter(
            ActivitySession.guild_id == guild_id,
            ActivitySession.user_id.in_(user_ids),
            ActivitySession.ended_at.is_not(None),
        )
        .group_by(ActivitySession.user_id, ActivitySession.game_id)
        .all()
    )
    for user_id, game_id, seconds in auto_rows:
        totals[(int(user_id), int(game_id))] = totals.get((int(user_id), int(game_id)), 0) + int(seconds or 0)

    hist_rows = (
        db.query(ManualPlaytime.user_id, ManualPlaytime.game_id, func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0))
        .filter(
            ManualPlaytime.guild_id == guild_id,
            ManualPlaytime.user_id.in_(user_ids),
            ManualPlaytime.deleted_at.is_(None),
        )
        .group_by(ManualPlaytime.user_id, ManualPlaytime.game_id)
        .all()
    )
    for user_id, game_id, seconds in hist_rows:
        totals[(int(user_id), int(game_id))] = totals.get((int(user_id), int(game_id)), 0) + int(seconds or 0)

    adj_rows = (
        db.query(
            PlaytimeAdjustment.user_id,
            PlaytimeAdjustment.game_id,
            func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0),
        )
        .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.user_id.in_(user_ids))
        .group_by(PlaytimeAdjustment.user_id, PlaytimeAdjustment.game_id)
        .all()
    )
    for user_id, game_id, seconds in adj_rows:
        totals[(int(user_id), int(game_id))] = totals.get((int(user_id), int(game_id)), 0) + int(seconds or 0)

    rows = []
    for (user_id, game_id), total in totals.items():
        if total <= 0:
            continue
        if user_id not in users or game_id not in games:
            continue
        rows.append((user_id, users[user_id], game_id, games[game_id], total))
    return rows


@router.get("/users")
def compare_users(
    guild_id: int = Query(...),
    user_ids: list[int] = Query(...),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_rows = (
        db.query(User.id, User.display_name)
        .filter(User.guild_id == guild_id, User.id.in_(user_ids), User.is_hidden.is_(False))
        .all()
    )

    totals = []
    for user_id, display_name in user_rows:
        automatic = (
            db.query(func.coalesce(func.sum(func.extract("epoch", ActivitySession.ended_at - ActivitySession.started_at)), 0))
            .filter(
                ActivitySession.guild_id == guild_id,
                ActivitySession.user_id == user_id,
                ActivitySession.ended_at.is_not(None),
            )
            .scalar()
            or 0
        )
        historical = (
            db.query(func.coalesce(func.sum(ManualPlaytime.duration_seconds), 0))
            .filter(ManualPlaytime.guild_id == guild_id, ManualPlaytime.user_id == user_id, ManualPlaytime.deleted_at.is_(None))
            .scalar()
            or 0
        )
        adjustments = (
            db.query(func.coalesce(func.sum(PlaytimeAdjustment.adjustment_seconds), 0))
            .filter(PlaytimeAdjustment.guild_id == guild_id, PlaytimeAdjustment.user_id == user_id)
            .scalar()
            or 0
        )
        totals.append(
            {
                "user_id": user_id,
                "display_name": display_name,
                "automatic_seconds": int(automatic),
                "historical_seconds": int(historical),
                "adjustment_seconds": int(adjustments),
                "total_seconds": max(0, int(automatic + historical + adjustments)),
            }
        )

    return totals


@router.get("/shared-games")
def shared_games(
    guild_id: int = Query(...),
    user_ids: list[int] = Query(...),
    _: object = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = _per_user_game_totals(db, guild_id, user_ids)

    per_game: dict[int, dict] = {}
    for user_id, user_name, game_id, game_name, total_seconds in rows:
        if int(total_seconds or 0) <= 0:
            continue
        item = per_game.setdefault(
            game_id,
            {
                "game_id": game_id,
                "game_name": game_name,
                "players": {},
            },
        )
        item["players"][str(user_id)] = {
            "user_id": user_id,
            "display_name": user_name,
            "total_seconds": max(0, int(total_seconds or 0)),
        }

    required = len(user_ids)
    result = []
    for game in per_game.values():
        if len(game["players"]) == required:
            result.append(game)

    result.sort(key=lambda x: x["game_name"].lower())
    return result
