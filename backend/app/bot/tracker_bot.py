from __future__ import annotations

from datetime import UTC, datetime

import discord
import structlog

from app.db.session import SessionLocal
from app.models import User
from app.services.session_service import (
    close_active_session,
    get_or_create_game,
    get_or_create_guild,
    get_or_create_user,
    start_session_if_needed,
)

logger = structlog.get_logger(__name__)


class DiscordTrackerBot(discord.Client):
    def __init__(self, settings, manager):
        intents = discord.Intents.none()
        intents.guilds = True
        intents.members = True
        intents.presences = True
        super().__init__(intents=intents)
        self.settings = settings
        self.manager = manager

    async def on_ready(self):
        try:
            self.manager.mark_connected(True)
            logger.info("discord_ready", user=str(self.user))

            guild = self.get_guild(self.settings.discord_guild_id)
            if not guild:
                logger.warning("guild_not_found", guild_id=self.settings.discord_guild_id)
                return

            db = SessionLocal()
            try:
                db_guild = get_or_create_guild(db, guild.id, guild.name)
                now = datetime.now(UTC)
                for member in guild.members:
                    if member.bot:
                        continue

                    user = get_or_create_user(
                        db,
                        db_guild.id,
                        member.id,
                        member.name,
                        member.display_name,
                        str(member.display_avatar.url) if member.display_avatar else None,
                    )

                    game = self._extract_game(member.activities)
                    if not game:
                        continue
                    db_game = get_or_create_game(db, game["name"], game.get("application_id"), None)
                    start_session_if_needed(db, db_guild.id, user.id, db_game.id, db_game.discord_application_id, started_at=now)
            finally:
                db.close()
        except Exception:
            logger.exception("on_ready_error")

    async def on_disconnect(self):
        try:
            self.manager.mark_connected(False)
        except Exception:
            logger.exception("on_disconnect_error")

    async def on_presence_update(self, before: discord.Member, after: discord.Member):
        try:
            if not after.guild or after.guild.id != self.settings.discord_guild_id:
                return
            if after.bot:
                return

            before_game = self._extract_game(before.activities)
            after_game = self._extract_game(after.activities)

            if before_game == after_game:
                return

            db = SessionLocal()
            try:
                db_guild = get_or_create_guild(db, after.guild.id, after.guild.name)
                user = get_or_create_user(
                    db,
                    db_guild.id,
                    after.id,
                    after.name,
                    after.display_name,
                    str(after.display_avatar.url) if after.display_avatar else None,
                )

                close_active_session(db, db_guild.id, user.id)
                if after_game:
                    game = get_or_create_game(db, after_game["name"], after_game.get("application_id"), None)
                    start_session_if_needed(db, db_guild.id, user.id, game.id, game.discord_application_id)

                self.manager.mark_event()
            finally:
                db.close()
        except Exception:
            logger.exception("on_presence_update_error")

    async def on_member_join(self, member: discord.Member):
        try:
            if member.bot:
                return
            if member.guild.id != self.settings.discord_guild_id:
                return

            db = SessionLocal()
            try:
                db_guild = get_or_create_guild(db, member.guild.id, member.guild.name)
                get_or_create_user(
                    db,
                    db_guild.id,
                    member.id,
                    member.name,
                    member.display_name,
                    str(member.display_avatar.url) if member.display_avatar else None,
                )
                logger.info("member_joined", user_id=member.id, username=member.name)
            finally:
                db.close()
        except Exception:
            logger.exception("on_member_join_error")

    async def on_member_remove(self, member: discord.Member):
        try:
            if member.bot:
                return
            if member.guild.id != self.settings.discord_guild_id:
                return

            db = SessionLocal()
            try:
                user = (
                    db.query(User)
                    .filter(User.guild_id == member.guild.id, User.discord_user_id == member.id)
                    .first()
                )
                if user:
                    user.is_active = False
                    db.commit()
                    logger.info("member_left", user_id=member.id, username=member.name)
            finally:
                db.close()
        except Exception:
            logger.exception("on_member_remove_error")

    def _extract_game(self, activities: tuple[discord.BaseActivity, ...]):
        for activity in activities:
            if activity.type != discord.ActivityType.playing:
                continue
            if not getattr(activity, "name", None):
                continue
            return {
                "name": activity.name,
                "application_id": int(activity.application_id) if getattr(activity, "application_id", None) else None,
            }
        return None
