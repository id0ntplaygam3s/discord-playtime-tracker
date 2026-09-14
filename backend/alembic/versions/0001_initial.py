"""initial schema

Revision ID: 0001_initial
Revises: 
Create Date: 2026-09-14
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


ACTIVITY_SOURCE_VALUES = ("discord", "manual")
MANUAL_SOURCE_VALUES = ("historical", "imported", "correction")
ADMIN_ROLE_VALUES = ("admin", "viewer")
AUDIT_ACTION_VALUES = (
    "manual_playtime_created",
    "manual_playtime_soft_deleted",
    "adjustment_created",
    "game_merged",
    "game_renamed",
    "csv_import",
)


def upgrade() -> None:
    pass

    op.create_table(
        "guilds",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_guild_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("discord_guild_id"),
    )
    op.create_index("ix_guilds_discord_guild_id", "guilds", ["discord_guild_id"])

    op.create_table(
        "admin_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("role IN ('admin', 'viewer')", name="ck_admin_users_role"),
        sa.UniqueConstraint("username"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.Integer(), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("discord_user_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("avatar_url", sa.String(length=1024), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("guild_id", "discord_user_id", name="uq_users_guild_discord_user"),
    )
    op.create_index("ix_users_guild_id", "users", ["guild_id"])

    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("discord_application_id", sa.BigInteger(), nullable=True),
        sa.Column("normalized_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("icon_url", sa.String(length=1024), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("discord_application_id", "normalized_name", name="uq_games_appid_name"),
        sa.UniqueConstraint("normalized_name", name="uq_games_normalized_name"),
    )
    op.create_index("ix_games_discord_application_id", "games", ["discord_application_id"])
    op.create_index("ix_games_normalized_name", "games", ["normalized_name"])

    op.create_table(
        "game_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("alias"),
    )

    op.create_table(
        "activity_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.Integer(), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activity_type", sa.String(length=64), nullable=False, server_default="playing"),
        sa.Column("source", sa.String(length=16), nullable=False, server_default="discord"),
        sa.Column("discord_application_id", sa.BigInteger(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("ended_at IS NULL OR ended_at >= started_at", name="ck_sessions_end_after_start"),
        sa.CheckConstraint("source IN ('discord', 'manual')", name="ck_sessions_source"),
    )
    op.create_index("ix_activity_sessions_guild_id", "activity_sessions", ["guild_id"])
    op.create_index("ix_activity_sessions_user_id", "activity_sessions", ["user_id"])
    op.create_index("ix_activity_sessions_game_id", "activity_sessions", ["game_id"])
    op.create_index("ix_activity_sessions_started_at", "activity_sessions", ["started_at"])
    op.create_index("ix_activity_sessions_ended_at", "activity_sessions", ["ended_at"])
    op.create_index("ix_sessions_user_started", "activity_sessions", ["user_id", "started_at"])
    op.create_index("ix_sessions_game_started", "activity_sessions", ["game_id", "started_at"])
    op.create_index(
        "uq_active_session_per_user",
        "activity_sessions",
        ["guild_id", "user_id"],
        unique=True,
        postgresql_where=sa.text("ended_at IS NULL"),
    )

    op.create_table(
        "manual_playtime",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.Integer(), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_manual_duration_non_negative"),
        sa.CheckConstraint("source IN ('historical', 'imported', 'correction')", name="ck_manual_playtime_source"),
    )

    op.create_table(
        "playtime_adjustments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.Integer(), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("adjustment_seconds", sa.Integer(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("guild_id", sa.Integer(), sa.ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("target_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target_game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="SET NULL"), nullable=True),
        sa.Column("change_seconds", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint(
            "action IN ('manual_playtime_created', 'manual_playtime_soft_deleted', 'adjustment_created', 'game_merged', 'game_renamed', 'csv_import')",
            name="ck_audit_logs_action",
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("playtime_adjustments")
    op.drop_table("manual_playtime")
    op.drop_index("uq_active_session_per_user", table_name="activity_sessions")
    op.drop_table("activity_sessions")
    op.drop_table("game_aliases")
    op.drop_table("games")
    op.drop_table("users")
    op.drop_table("admin_users")
    op.drop_table("guilds")

    pass
