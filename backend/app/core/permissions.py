from __future__ import annotations

PERMISSIONS = {
    "dashboard.view": "View dashboard",
    "games.view": "View games",
    "users.view": "View users",
    "users.manage": "Manage users/accounts",
    "playtime.view": "View playtime",
    "playtime.manage_own": "Manage own playtime",
    "playtime.manage_all": "Manage all playtime",
    "imports.view": "View imports",
    "imports.manage": "Manage imports",
    "audit.view": "View audit log",
    "registrations.view": "View registrations",
    "registrations.manage": "Manage registrations",
    "settings.view": "View settings",
    "settings.manage": "Manage settings",
    "accounts.reset_password": "Reset passwords",
    "accounts.unlock": "Unlock accounts",
    "accounts.disable": "Disable accounts",
    "permissions.view": "View permissions",
    "permissions.manage": "Manage permissions",
}


class PermissionCode:
    DASHBOARD_VIEW = "dashboard.view"
    GAMES_VIEW = "games.view"
    USERS_VIEW = "users.view"
    USERS_MANAGE = "users.manage"
    PLAYTIME_VIEW = "playtime.view"
    PLAYTIME_MANAGE_OWN = "playtime.manage_own"
    PLAYTIME_MANAGE_ALL = "playtime.manage_all"
    IMPORTS_VIEW = "imports.view"
    IMPORTS_MANAGE = "imports.manage"
    AUDIT_VIEW = "audit.view"
    REGISTRATIONS_VIEW = "registrations.view"
    REGISTRATIONS_MANAGE = "registrations.manage"
    SETTINGS_VIEW = "settings.view"
    SETTINGS_MANAGE = "settings.manage"
    ACCOUNTS_RESET_PASSWORD = "accounts.reset_password"
    ACCOUNTS_UNLOCK = "accounts.unlock"
    ACCOUNTS_DISABLE = "accounts.disable"
    PERMISSIONS_VIEW = "permissions.view"
    PERMISSIONS_MANAGE = "permissions.manage"
