from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import AppSetting

DEFAULT_SETTINGS: dict[str, object] = {
    "application_name": "Discord Playtime Tracker",
    "guest_access_enabled": True,
    "registration_enabled": True,
    "registration_requires_approval": True,
    "default_registration_role": "user",
    "auth_min_password_length": 8,
    "auth_max_failed_login_attempts": 5,
    "auth_lock_minutes": 30,
    "dashboard_default_range": "30d",
    "dashboard_selected_game_default_range": "all",
    "users_can_create_own_manual": True,
    "users_can_edit_own_manual": True,
    "users_can_delete_own_manual": True,
}


def ensure_default_settings(db: Session) -> None:
    for key, value in DEFAULT_SETTINGS.items():
        row = db.query(AppSetting).filter(AppSetting.key == key).first()
        if row is None:
            db.add(AppSetting(key=key, value_json=value))
    db.flush()


def get_setting(db: Session, key: str, fallback: object | None = None):
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is not None:
        return row.value_json
    if key in DEFAULT_SETTINGS:
        return DEFAULT_SETTINGS[key]
    return fallback


def get_all_settings(db: Session) -> dict[str, object]:
    values = dict(DEFAULT_SETTINGS)
    rows = db.query(AppSetting).all()
    for row in rows:
        values[row.key] = row.value_json
    return values


def set_setting(db: Session, key: str, value: object, updated_by_admin_user_id: int | None = None) -> AppSetting:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    if row is None:
        row = AppSetting(key=key)
        db.add(row)
    row.value_json = value
    row.updated_by_admin_user_id = updated_by_admin_user_id
    db.flush()
    return row
