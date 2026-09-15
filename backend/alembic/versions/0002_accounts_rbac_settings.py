"""accounts, rbac, settings, and password reset

Revision ID: 0002_accounts_rbac_settings
Revises: 0001_initial
Create Date: 2026-09-15
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_accounts_rbac_settings"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table(
        "app_roles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=16), nullable=False),
        sa.Column("display_name", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("name IN ('guest', 'user', 'admin')", name="ck_app_roles_name"),
        sa.UniqueConstraint("name", name="uq_app_roles_name"),
    )

    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"])

    op.create_table(
        "role_permissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("app_roles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    op.create_table(
        "user_accounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role_id", sa.Integer(), sa.ForeignKey("app_roles.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disabled_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'active', 'locked', 'disabled')", name="ck_user_accounts_status"),
        sa.UniqueConstraint("user_id", name="uq_user_accounts_user_id"),
    )
    op.create_index("ix_user_accounts_user_id", "user_accounts", ["user_id"])
    op.create_index("ix_user_accounts_role_id", "user_accounts", ["role_id"])
    op.create_index("ix_user_accounts_status", "user_accounts", ["status"])

    op.create_table(
        "user_permission_overrides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("permission_id", sa.Integer(), sa.ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("is_allowed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("account_id", "permission_id", name="uq_user_permission_override"),
    )
    op.create_index("ix_user_permission_overrides_account_id", "user_permission_overrides", ["account_id"])
    op.create_index("ix_user_permission_overrides_permission_id", "user_permission_overrides", ["permission_id"])

    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=True),
        sa.Column("updated_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("key", name="uq_app_settings_key"),
    )
    op.create_index("ix_app_settings_key", "app_settings", ["key"])

    op.create_table(
        "password_reset_requests",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("account_id", sa.Integer(), sa.ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("token_hash", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approved_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_admin_user_id", sa.Integer(), sa.ForeignKey("admin_users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'approved', 'completed', 'rejected', 'expired')", name="ck_password_reset_requests_status"),
    )
    op.create_index("ix_password_reset_requests_account_id", "password_reset_requests", ["account_id"])
    op.create_index("ix_password_reset_requests_status", "password_reset_requests", ["status"])
    op.create_index("ix_password_reset_requests_token_hash", "password_reset_requests", ["token_hash"])
    op.create_index("ix_password_reset_requests_expires_at", "password_reset_requests", ["expires_at"])

    op.execute("INSERT INTO app_roles (name, display_name) VALUES ('guest', 'Guest'), ('user', 'User'), ('admin', 'Admin')")

    permission_rows = [
        ("dashboard.view", "View dashboard"),
        ("games.view", "View games"),
        ("users.view", "View users"),
        ("users.manage", "Manage users/accounts"),
        ("playtime.view", "View playtime"),
        ("playtime.manage_own", "Manage own playtime"),
        ("playtime.manage_all", "Manage all playtime"),
        ("imports.view", "View imports"),
        ("imports.manage", "Manage imports"),
        ("audit.view", "View audit log"),
        ("registrations.view", "View registrations"),
        ("registrations.manage", "Manage registrations"),
        ("settings.view", "View settings"),
        ("settings.manage", "Manage settings"),
        ("accounts.reset_password", "Reset passwords"),
        ("accounts.unlock", "Unlock accounts"),
        ("accounts.disable", "Disable accounts"),
        ("permissions.view", "View permissions"),
        ("permissions.manage", "Manage permissions"),
    ]
    for code, description in permission_rows:
        op.execute(
            sa.text(
                "INSERT INTO permissions (code, description) VALUES (:code, :description)"
            ).bindparams(code=code, description=description)
        )

    # Guest defaults
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, is_allowed)
        SELECT r.id, p.id, true
        FROM app_roles r
        JOIN permissions p ON p.code IN ('dashboard.view', 'games.view', 'playtime.view')
        WHERE r.name = 'guest'
        """
    )

    # User role defaults
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, is_allowed)
        SELECT r.id, p.id, true
        FROM app_roles r
        JOIN permissions p ON p.code IN ('dashboard.view', 'games.view', 'users.view', 'playtime.view', 'playtime.manage_own')
        WHERE r.name = 'user'
        """
    )

    # Admin gets all permissions
    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id, is_allowed)
        SELECT r.id, p.id, true
        FROM app_roles r
        CROSS JOIN permissions p
        WHERE r.name = 'admin'
        """
    )

    # Runtime defaults stored in DB settings.
    op.execute(
        """
        INSERT INTO app_settings (key, value_json)
        VALUES
            ('application_name', '"Discord Playtime Tracker"'),
            ('guest_access_enabled', 'true'),
            ('registration_enabled', 'true'),
            ('registration_requires_approval', 'true'),
            ('default_registration_role', '"user"'),
            ('auth_min_password_length', '8'),
            ('auth_max_failed_login_attempts', '5'),
            ('auth_lock_minutes', '30'),
            ('dashboard_default_range', '"30d"'),
            ('dashboard_selected_game_default_range', '"all"'),
            ('users_can_create_own_manual', 'true'),
            ('users_can_edit_own_manual', 'true'),
            ('users_can_delete_own_manual', 'true')
        """
    )

    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_audit_logs_action", "audit_logs", type_="check")
        op.create_check_constraint(
            "ck_audit_logs_action",
            "audit_logs",
            "action IN ('manual_playtime_created', 'manual_playtime_soft_deleted', 'adjustment_created', 'game_merged', 'game_renamed', 'csv_import', 'registration_submitted', 'registration_approved', 'registration_rejected', 'login_success', 'login_failure', 'account_locked', 'account_unlocked', 'account_disabled', 'account_enabled', 'password_reset_requested', 'password_reset_approved', 'password_reset_completed', 'role_changed', 'permission_changed', 'user_account_changed', 'settings_changed')",
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        op.drop_constraint("ck_audit_logs_action", "audit_logs", type_="check")
        op.create_check_constraint(
            "ck_audit_logs_action",
            "audit_logs",
            "action IN ('manual_playtime_created', 'manual_playtime_soft_deleted', 'adjustment_created', 'game_merged', 'game_renamed', 'csv_import')",
        )

    op.drop_table("password_reset_requests")
    op.drop_table("app_settings")
    op.drop_table("user_permission_overrides")
    op.drop_table("user_accounts")
    op.drop_table("role_permissions")
    op.drop_table("permissions")
    op.drop_table("app_roles")
