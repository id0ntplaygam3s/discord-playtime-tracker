from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BIGINT,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Role(str, enum.Enum):
    admin = "admin"
    viewer = "viewer"


class AccountStatus(str, enum.Enum):
    pending = "pending"
    active = "active"
    locked = "locked"
    disabled = "disabled"


class AppRoleName(str, enum.Enum):
    guest = "guest"
    user = "user"
    admin = "admin"


class ManualSource(str, enum.Enum):
    historical = "historical"
    imported = "imported"
    correction = "correction"


class ActivitySource(str, enum.Enum):
    discord = "discord"
    manual = "manual"


class AuditAction(str, enum.Enum):
    manual_playtime_created = "manual_playtime_created"
    manual_playtime_soft_deleted = "manual_playtime_soft_deleted"
    adjustment_created = "adjustment_created"
    game_merged = "game_merged"
    game_renamed = "game_renamed"
    csv_import = "csv_import"
    registration_submitted = "registration_submitted"
    registration_approved = "registration_approved"
    registration_rejected = "registration_rejected"
    login_success = "login_success"
    login_failure = "login_failure"
    account_locked = "account_locked"
    account_unlocked = "account_unlocked"
    account_disabled = "account_disabled"
    account_enabled = "account_enabled"
    password_reset_requested = "password_reset_requested"
    password_reset_approved = "password_reset_approved"
    password_reset_completed = "password_reset_completed"
    role_changed = "role_changed"
    permission_changed = "permission_changed"
    user_account_changed = "user_account_changed"
    settings_changed = "settings_changed"
    game_created = "game_created"
    game_canonical_changed = "game_canonical_changed"
    game_unmerged = "game_unmerged"
    merge_suggestion_ignored = "merge_suggestion_ignored"
    merge_suggestion_accepted = "merge_suggestion_accepted"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Guild(Base, TimestampMixin):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    discord_guild_id: Mapped[int] = mapped_column(BIGINT, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    users = relationship("User", back_populates="guild")


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    discord_user_id: Mapped[int] = mapped_column(BIGINT, nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(1024))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    guild = relationship("Guild", back_populates="users")

    __table_args__ = (UniqueConstraint("guild_id", "discord_user_id", name="uq_users_guild_discord_user"),)


class AppRole(Base, TimestampMixin):
    __tablename__ = "app_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[AppRoleName] = mapped_column(
        Enum(AppRoleName, name="app_role_name", native_enum=False),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)

    permissions = relationship("RolePermission", back_populates="role")


class Permission(Base, TimestampMixin):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(String(255))

    roles = relationship("RolePermission", back_populates="permission")


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("app_roles.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    role = relationship("AppRole", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class UserAccount(Base, TimestampMixin):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("app_roles.id", ondelete="RESTRICT"), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, name="account_status", native_enum=False),
        default=AccountStatus.pending,
        nullable=False,
        index=True,
    )
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    rejected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disabled_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)

    user = relationship("User")
    role = relationship("AppRole")


class UserPermissionOverride(Base, TimestampMixin):
    __tablename__ = "user_permission_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True)
    is_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False)

    __table_args__ = (UniqueConstraint("account_id", "permission_id", name="uq_user_permission_override"),)

    account = relationship("UserAccount")
    permission = relationship("Permission")


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    value_json: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSON, nullable=True)
    updated_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)


class PasswordResetStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    completed = "completed"
    rejected = "rejected"
    expired = "expired"


class PasswordResetRequest(Base, TimestampMixin):
    __tablename__ = "password_reset_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[PasswordResetStatus] = mapped_column(
        Enum(PasswordResetStatus, name="password_reset_status", native_enum=False),
        default=PasswordResetStatus.pending,
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str | None] = mapped_column(String(255), index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    approved_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejected_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)


class Game(Base, TimestampMixin):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="SET NULL"), index=True)
    discord_application_id: Mapped[int | None] = mapped_column(BIGINT, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(1024))
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __table_args__ = (
        UniqueConstraint("discord_application_id", "normalized_name", name="uq_games_appid_name"),
        UniqueConstraint("normalized_name", name="uq_games_normalized_name"),
        CheckConstraint("canonical_game_id IS NULL OR canonical_game_id <> id", name="ck_games_no_self_canonical"),
    )

    canonical_game = relationship("Game", remote_side=[id], uselist=False)


class GameAlias(Base, TimestampMixin):
    __tablename__ = "game_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)


class MergeSuggestionStatus(str, enum.Enum):
    ignored = "ignored"
    accepted = "accepted"


class GameMergeSuggestionState(Base, TimestampMixin):
    __tablename__ = "game_merge_suggestion_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    target_game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[MergeSuggestionStatus] = mapped_column(
        Enum(MergeSuggestionStatus, name="merge_suggestion_status", native_enum=False),
        nullable=False,
        default=MergeSuggestionStatus.ignored,
    )
    decided_by_admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    decided_by_account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id", ondelete="SET NULL"), index=True)

    __table_args__ = (
        UniqueConstraint("source_game_id", "target_game_id", name="uq_merge_suggestion_pair"),
        CheckConstraint("source_game_id <> target_game_id", name="ck_merge_suggestion_not_self"),
    )


class ActivitySession(Base, TimestampMixin):
    __tablename__ = "activity_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="RESTRICT"), nullable=False, index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    activity_type: Mapped[str] = mapped_column(String(64), default="playing", nullable=False)
    source: Mapped[ActivitySource] = mapped_column(
        Enum(ActivitySource, name="activity_source", native_enum=False),
        default=ActivitySource.discord,
    )
    discord_application_id: Mapped[int | None] = mapped_column(BIGINT, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)

    __table_args__ = (
        CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_sessions_end_after_start"),
        Index("ix_sessions_user_started", "user_id", "started_at"),
        Index("ix_sessions_game_started", "game_id", "started_at"),
    )


class ManualPlaytime(Base, TimestampMixin):
    __tablename__ = "manual_playtime"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="RESTRICT"), nullable=False, index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[ManualSource] = mapped_column(Enum(ManualSource, name="manual_source", native_enum=False), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (CheckConstraint("duration_seconds >= 0", name="ck_manual_duration_non_negative"),)


class PlaytimeAdjustment(Base):
    __tablename__ = "playtime_adjustments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id", ondelete="RESTRICT"), nullable=False, index=True)
    adjustment_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AdminUser(Base, TimestampMixin):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Role] = mapped_column(Enum(Role, name="admin_role", native_enum=False), default=Role.admin, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    guild_id: Mapped[int] = mapped_column(ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True)
    admin_user_id: Mapped[int | None] = mapped_column(ForeignKey("admin_users.id", ondelete="SET NULL"), index=True)
    actor_account_id: Mapped[int | None] = mapped_column(ForeignKey("user_accounts.id", ondelete="SET NULL"), index=True)
    actor_type: Mapped[str | None] = mapped_column(String(32), index=True)
    actor_label: Mapped[str | None] = mapped_column(String(128))
    action: Mapped[AuditAction] = mapped_column(Enum(AuditAction, name="audit_action", native_enum=False), nullable=False)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    target_game_id: Mapped[int | None] = mapped_column(ForeignKey("games.id", ondelete="SET NULL"), index=True)
    change_seconds: Mapped[int | None] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
