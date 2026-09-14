from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import ActivitySession, Game, ManualPlaytime, PlaytimeAdjustment, User

router = APIRouter(prefix="/exports", tags=["exports"])


def _stream_csv(rows: list[dict], filename: str) -> StreamingResponse:
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    else:
        output.write("\n")

    response = StreamingResponse(iter([output.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    return response


@router.get("/users")
def export_users(guild_id: int = Query(...), _=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(User).filter(User.guild_id == guild_id).all()
    payload = [{"id": u.id, "discord_user_id": u.discord_user_id, "display_name": u.display_name} for u in rows]
    return _stream_csv(payload, "users.csv")


@router.get("/games")
def export_games(_=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(Game).all()
    payload = [{"id": g.id, "display_name": g.display_name, "normalized_name": g.normalized_name} for g in rows]
    return _stream_csv(payload, "games.csv")


@router.get("/sessions")
def export_sessions(guild_id: int = Query(...), _=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(ActivitySession).filter(ActivitySession.guild_id == guild_id).all()
    payload = [
        {
            "id": s.id,
            "user_id": s.user_id,
            "game_id": s.game_id,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
        }
        for s in rows
    ]
    return _stream_csv(payload, "sessions.csv")


@router.get("/manual")
def export_manual(guild_id: int = Query(...), _=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(ManualPlaytime).filter(ManualPlaytime.guild_id == guild_id).all()
    payload = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "game_id": r.game_id,
            "duration_seconds": r.duration_seconds,
            "source": r.source.value,
            "note": r.note,
        }
        for r in rows
    ]
    return _stream_csv(payload, "manual_playtime.csv")


@router.get("/adjustments")
def export_adjustments(guild_id: int = Query(...), _=Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(PlaytimeAdjustment).filter(PlaytimeAdjustment.guild_id == guild_id).all()
    payload = [
        {
            "id": r.id,
            "user_id": r.user_id,
            "game_id": r.game_id,
            "adjustment_seconds": r.adjustment_seconds,
            "reason": r.reason,
            "created_at": r.created_at,
        }
        for r in rows
    ]
    return _stream_csv(payload, "adjustments.csv")
