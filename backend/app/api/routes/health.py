from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    return {"status": "ok", "version": settings.app_version}


@router.get("/bot-status")
def bot_status(request: Request, db: Session = Depends(get_db)):
    """Public bot status endpoint - no authentication required."""
    manager = request.app.state.bot_manager
    connected = hasattr(manager, 'connected') and manager.connected

    uptime = None
    if hasattr(manager, 'started_at') and manager.started_at:
        uptime = int((datetime.now(UTC) - manager.started_at).total_seconds())

    last_event = None
    if hasattr(manager, 'last_event_at') and manager.last_event_at:
        last_event = manager.last_event_at

    return {
        "connected": connected,
        "bot_uptime_seconds": uptime,
        "last_event_at": last_event,
    }
