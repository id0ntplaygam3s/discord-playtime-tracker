from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.models import AdminUser, AuditLog, Game, User

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
def audit_log(
    guild_id: int = Query(...),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    rows = (
        db.query(AuditLog, AdminUser, User, Game)
        .join(AdminUser, AdminUser.id == AuditLog.admin_user_id, isouter=True)
        .join(User, User.id == AuditLog.target_user_id, isouter=True)
        .join(Game, Game.id == AuditLog.target_game_id, isouter=True)
        .filter(AuditLog.guild_id == guild_id)
        .order_by(desc(AuditLog.created_at))
        .offset(offset)
        .limit(page_size)
        .all()
    )

    return [
        {
            "date": log.created_at,
            "administrator": admin.username if admin else None,
            "user": user.display_name if user else None,
            "game": game.display_name if game else None,
            "action": log.action.value,
            "change_seconds": log.change_seconds,
            "reason": log.reason,
        }
        for log, admin, user, game in rows
    ]
