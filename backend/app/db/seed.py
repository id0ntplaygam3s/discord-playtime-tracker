from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.models import AdminUser, Guild, Role
from app.services.authz_service import ensure_roles_and_permissions
from app.services.settings_service import ensure_default_settings


def seed_initial_data(db: Session, settings: Settings) -> None:
    guild = db.query(Guild).filter(Guild.discord_guild_id == settings.discord_guild_id).first()
    if not guild and settings.discord_guild_id:
        guild = Guild(discord_guild_id=settings.discord_guild_id, name=f"Guild {settings.discord_guild_id}")
        db.add(guild)

    admin = db.query(AdminUser).filter(AdminUser.username == settings.admin_username).first()
    if not admin:
        db.add(
            AdminUser(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
                role=Role.admin,
            )
        )

    ensure_roles_and_permissions(db)
    ensure_default_settings(db)

    db.commit()
