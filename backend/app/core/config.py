from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(alias="DATABASE_URL")
    discord_bot_token: str = Field(default="", alias="DISCORD_BOT_TOKEN")
    discord_guild_id: int = Field(default=0, alias="DISCORD_GUILD_ID")
    steam_api_key: str = Field(default="", alias="STEAM_API_KEY")

    timezone: str = Field(default="Europe/London", alias="TIMEZONE")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO", alias="LOG_LEVEL")

    admin_username: str = Field(default="admin", alias="ADMIN_USERNAME")
    admin_password: str = Field(alias="ADMIN_PASSWORD")
    secret_key: str = Field(alias="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    session_retention_days: int | None = Field(default=None, alias="SESSION_RETENTION_DAYS")
    retention_check_interval_minutes: int = Field(default=60, alias="RETENTION_CHECK_INTERVAL_MINUTES")
    cors_allow_origins: str = Field(default="*", alias="CORS_ALLOW_ORIGINS")
    testing: bool = Field(default=False, alias="TESTING")

    @property
    def cors_allow_origins_list(self) -> list[str]:
        raw = self.cors_allow_origins.strip()
        if not raw:
            return []
        if raw == "*":
            return ["*"]
        return [item.strip() for item in raw.split(",") if item.strip()]

    @field_validator("session_retention_days", mode="before")
    @classmethod
    def parse_optional_int_blank(cls, value):
        if value in ("", None):
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
