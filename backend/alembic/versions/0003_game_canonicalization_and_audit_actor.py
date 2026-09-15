"""game canonicalization, suggestion state, and unified audit actor

Revision ID: 0003_game_canonicalization_and_audit_actor
Revises: 0002_accounts_rbac_settings
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_game_canonicalization_and_audit_actor"
down_revision = "0002_accounts_rbac_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("games", sa.Column("canonical_game_id", sa.Integer(), nullable=True))
    op.create_index("ix_games_canonical_game_id", "games", ["canonical_game_id"])
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_games_canonical_game_id", "games", "games", ["canonical_game_id"], ["id"], ondelete="SET NULL")
        op.create_check_constraint("ck_games_no_self_canonical", "games", "canonical_game_id IS NULL OR canonical_game_id <> id")

    op.add_column("game_aliases", sa.Column("normalized_alias", sa.String(length=255), nullable=True))
    op.create_index("ix_game_aliases_normalized_alias", "game_aliases", ["normalized_alias"], unique=True)

    rows = bind.execute(sa.text("SELECT id, alias FROM game_aliases")).fetchall()
    for row in rows:
        alias = (row.alias or "").strip().lower()
        alias = alias.replace("\u2122", "").replace("\u00ae", "").replace("\u00a9", "")
        alias = " ".join(alias.split())
        bind.execute(
            sa.text("UPDATE game_aliases SET normalized_alias = :normalized_alias WHERE id = :id"),
            {"normalized_alias": alias, "id": row.id},
        )

    if bind.dialect.name != "sqlite":
        op.alter_column("game_aliases", "normalized_alias", nullable=False)
    else:
        # SQLite cannot alter nullability cleanly in-place; values are fully backfilled.
        pass

    op.add_column("audit_logs", sa.Column("actor_account_id", sa.Integer(), nullable=True))
    op.add_column("audit_logs", sa.Column("actor_type", sa.String(length=32), nullable=True))
    op.add_column("audit_logs", sa.Column("actor_label", sa.String(length=128), nullable=True))
    if bind.dialect.name != "sqlite":
        op.create_foreign_key("fk_audit_logs_actor_account_id", "audit_logs", "user_accounts", ["actor_account_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_audit_logs_actor_account_id", "audit_logs", ["actor_account_id"])
    op.create_index("ix_audit_logs_actor_type", "audit_logs", ["actor_type"])

    op.create_table(
        "game_merge_suggestion_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_game_id", sa.Integer(), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ignored"),
        sa.Column("decided_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("decided_by_account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('ignored', 'accepted')", name="ck_merge_suggestion_status"),
        sa.CheckConstraint("source_game_id <> target_game_id", name="ck_merge_suggestion_not_self"),
        sa.UniqueConstraint("source_game_id", "target_game_id", name="uq_merge_suggestion_pair"),
    )
    op.create_index("ix_game_merge_suggestion_state_source_game_id", "game_merge_suggestion_state", ["source_game_id"])
    op.create_index("ix_game_merge_suggestion_state_target_game_id", "game_merge_suggestion_state", ["target_game_id"])

    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_audit_logs_action", "audit_logs", type_="check")
        op.create_check_constraint(
            "ck_audit_logs_action",
            "audit_logs",
            "action IN ('manual_playtime_created', 'manual_playtime_soft_deleted', 'adjustment_created', 'game_merged', 'game_renamed', 'csv_import', 'registration_submitted', 'registration_approved', 'registration_rejected', 'login_success', 'login_failure', 'account_locked', 'account_unlocked', 'account_disabled', 'account_enabled', 'password_reset_requested', 'password_reset_approved', 'password_reset_completed', 'role_changed', 'permission_changed', 'user_account_changed', 'settings_changed', 'game_created', 'game_canonical_changed', 'game_unmerged', 'merge_suggestion_ignored', 'merge_suggestion_accepted')",
        )


def downgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_audit_logs_action", "audit_logs", type_="check")
        op.create_check_constraint(
            "ck_audit_logs_action",
            "audit_logs",
            "action IN ('manual_playtime_created', 'manual_playtime_soft_deleted', 'adjustment_created', 'game_merged', 'game_renamed', 'csv_import', 'registration_submitted', 'registration_approved', 'registration_rejected', 'login_success', 'login_failure', 'account_locked', 'account_unlocked', 'account_disabled', 'account_enabled', 'password_reset_requested', 'password_reset_approved', 'password_reset_completed', 'role_changed', 'permission_changed', 'user_account_changed', 'settings_changed')",
        )

    op.drop_table("game_merge_suggestion_state")

    op.drop_index("ix_audit_logs_actor_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_account_id", table_name="audit_logs")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_audit_logs_actor_account_id", "audit_logs", type_="foreignkey")
    op.drop_column("audit_logs", "actor_label")
    op.drop_column("audit_logs", "actor_type")
    op.drop_column("audit_logs", "actor_account_id")

    op.drop_index("ix_game_aliases_normalized_alias", table_name="game_aliases")
    op.drop_column("game_aliases", "normalized_alias")

    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_games_no_self_canonical", "games", type_="check")
    op.drop_index("ix_games_canonical_game_id", table_name="games")
    if bind.dialect.name != "sqlite":
        op.drop_constraint("fk_games_canonical_game_id", "games", type_="foreignkey")
    op.drop_column("games", "canonical_game_id")
