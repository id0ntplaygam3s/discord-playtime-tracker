from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.db.session import get_db
from app.workers.demo_data import seed_demo_data

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/demo-data")
def generate_demo_data(
    guild_id: int = Query(...),
    days: int = Query(default=30, ge=1, le=365),
    _=Depends(require_admin),
    db: Session = Depends(get_db),
):
    seed_demo_data(db, guild_id, days=days)
    return {"ok": True}
