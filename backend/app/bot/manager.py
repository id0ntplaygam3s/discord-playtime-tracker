from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.bot.tracker_bot import DiscordTrackerBot
from app.core.config import Settings
from app.db.session import SessionLocal
from app.models import Guild
from app.services.session_service import close_all_active_sessions_for_guild

logger = structlog.get_logger(__name__)


class BotManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._bot: DiscordTrackerBot | None = None
        self._task: asyncio.Task | None = None
        self.started_at: datetime | None = None
        self.last_event_at: datetime | None = None
        self.connected = False

    async def start(self) -> None:
        if not self.settings.discord_bot_token or not self.settings.discord_guild_id:
            logger.info("discord_bot_disabled", reason="missing token or guild id")
            return

        self._bot = DiscordTrackerBot(self.settings, self)
        self.started_at = datetime.now(timezone.utc)

        db: Session = SessionLocal()
        try:
            db_guild = db.query(Guild).filter(Guild.discord_guild_id == self.settings.discord_guild_id).first()
            if db_guild:
                close_all_active_sessions_for_guild(db, db_guild.id, ended_at=self.started_at)
        finally:
            db.close()

        self._task = asyncio.create_task(self._bot.start(self.settings.discord_bot_token))

    async def stop(self) -> None:
        if self._bot:
            await self._bot.close()
        if self._task:
            self._task.cancel()

    def mark_connected(self, connected: bool) -> None:
        self.connected = connected

    def mark_event(self) -> None:
        self.last_event_at = datetime.now(timezone.utc)
