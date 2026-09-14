from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import ActivitySession, AuditAction, AuditLog, Game, Guild, User
from app.services.normalization import normalize_game_name


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_or_create_user(db: Session, guild_id: int, discord_user_id: int, username: str, display_name: str, avatar_url: str | None) -> User:
    user = db.query(User).filter(User.guild_id == guild_id, User.discord_user_id == discord_user_id).first()
    if user:
        user.username = username
        user.display_name = display_name
        user.avatar_url = avatar_url
        user.last_seen_at = now_utc()
        db.commit()
        db.refresh(user)
        return user

    user = User(
        guild_id=guild_id,
        discord_user_id=discord_user_id,
        username=username,
        display_name=display_name,
        avatar_url=avatar_url,
        first_seen_at=now_utc(),
        last_seen_at=now_utc(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_or_create_guild(db: Session, discord_guild_id: int, name: str) -> Guild:
    guild = db.query(Guild).filter(Guild.discord_guild_id == discord_guild_id).first()
    if guild:
        guild.name = name
        db.commit()
        db.refresh(guild)
        return guild
    guild = Guild(discord_guild_id=discord_guild_id, name=name)
    db.add(guild)
    db.commit()
    db.refresh(guild)
    return guild


def get_or_create_game(
    db: Session,
    game_name: str,
    discord_application_id: int | None,
    icon_url: str | None,
    commit: bool = True,
) -> Game:
    normalized = normalize_game_name(game_name)

    game = None
    if discord_application_id:
        game = db.query(Game).filter(Game.discord_application_id == discord_application_id).first()

    if not game:
        game = db.query(Game).filter(Game.normalized_name == normalized).first()

    if game:
        game.display_name = game_name
        game.last_seen_at = now_utc()
        if icon_url:
            game.icon_url = icon_url
        if discord_application_id and not game.discord_application_id:
            game.discord_application_id = discord_application_id
        if commit:
            db.commit()
            db.refresh(game)
        else:
            db.flush()
        return game

    game = Game(
        discord_application_id=discord_application_id,
        normalized_name=normalized,
        display_name=game_name,
        icon_url=icon_url,
        first_seen_at=now_utc(),
        last_seen_at=now_utc(),
    )
    db.add(game)
    if commit:
        db.commit()
        db.refresh(game)
    else:
        db.flush()
    return game


def close_active_session(db: Session, guild_id: int, user_id: int, ended_at: datetime | None = None) -> ActivitySession | None:
    active = (
        db.query(ActivitySession)
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.user_id == user_id, ActivitySession.ended_at.is_(None))
        .order_by(ActivitySession.started_at.desc())
        .first()
    )
    if not active:
        return None
    active.ended_at = ended_at or now_utc()
    if active.ended_at < active.started_at:
        active.ended_at = active.started_at
    db.commit()
    db.refresh(active)
    return active


def start_session_if_needed(
    db: Session,
    guild_id: int,
    user_id: int,
    game_id: int,
    discord_application_id: int | None,
    started_at: datetime | None = None,
) -> ActivitySession:
    started_at = started_at or now_utc()

    active = (
        db.query(ActivitySession)
        .filter(ActivitySession.guild_id == guild_id, ActivitySession.user_id == user_id, ActivitySession.ended_at.is_(None))
        .first()
    )
    if active and active.game_id == game_id:
        return active
    if active and active.game_id != game_id:
        active.ended_at = started_at

    session = ActivitySession(
        guild_id=guild_id,
        user_id=user_id,
        game_id=game_id,
        started_at=started_at,
        ended_at=None,
        activity_type="playing",
        discord_application_id=discord_application_id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def close_all_active_sessions_for_guild(db: Session, guild_id: int, ended_at: datetime | None = None) -> int:
    ended_at = ended_at or now_utc()
    sessions = db.query(ActivitySession).filter(ActivitySession.guild_id == guild_id, ActivitySession.ended_at.is_(None)).all()
    for item in sessions:
        item.ended_at = max(item.started_at, ended_at)
    db.commit()
    return len(sessions)


def write_audit_log(
    db: Session,
    guild_id: int,
    action: AuditAction,
    admin_user_id: int | None,
    target_user_id: int | None,
    target_game_id: int | None,
    change_seconds: int | None,
    reason: str | None,
    metadata_json: dict | None = None,
    commit: bool = True,
) -> None:
    db.add(
        AuditLog(
            guild_id=guild_id,
            action=action,
            admin_user_id=admin_user_id,
            target_user_id=target_user_id,
            target_game_id=target_game_id,
            change_seconds=change_seconds,
            reason=reason,
            metadata_json=metadata_json,
        )
    )
    if commit:
        db.commit()
