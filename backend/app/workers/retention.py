from __future__ import annotations

import asyncio
import contextlib
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import SessionLocal
from app.models import ActivitySession

logger = structlog.get_logger(__name__)


class RetentionWorker:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if not self.settings.session_retention_days:
            logger.info("retention_disabled", reason="session_retention_days not configured")
            return
        if self.settings.session_retention_days <= 0:
            logger.info("retention_disabled", reason="session_retention_days must be > 0")
            return

        logger.info(
            "retention_worker_starting",
            retention_days=self.settings.session_retention_days,
            interval_minutes=self.settings.retention_check_interval_minutes,
        )
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        self._stop_event.set()
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                deleted = self._cleanup_once()
                logger.info("retention_cleanup_complete", deleted_sessions=deleted)
            except Exception:
                logger.exception("retention_cleanup_failed")

            wait_seconds = max(60, self.settings.retention_check_interval_minutes * 60)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=wait_seconds)
            except asyncio.TimeoutError:
                continue

    def _cleanup_once(self) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.settings.session_retention_days or 0)
        db: Session = SessionLocal()
        try:
            deleted = (
                db.query(ActivitySession)
                .filter(
                    ActivitySession.ended_at.is_not(None),
                    ActivitySession.ended_at < cutoff,
                )
                .delete(synchronize_session=False)
            )
            db.commit()
            return int(deleted or 0)
        finally:
            db.close()
