from __future__ import annotations

from datetime import datetime, timedelta, timezone
import random

from sqlalchemy.orm import Session

from app.models import ActivitySession, Game, Guild, ManualPlaytime, ManualSource, PlaytimeAdjustment, User


def seed_demo_data(db: Session, guild_id: int, days: int = 30) -> None:
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        return

    names = ["John", "Sarah", "Bob", "Alex", "Kai"]
    games = ["Minecraft", "Helldivers 2", "VALORANT", "Terraria", "Apex Legends"]

    users = []
    for idx, name in enumerate(names, start=1):
        user = db.query(User).filter(User.guild_id == guild_id, User.display_name == name).first()
        if not user:
            user = User(
                guild_id=guild_id,
                discord_user_id=100000 + idx,
                username=name.lower(),
                display_name=name,
            )
            db.add(user)
            db.flush()
        users.append(user)

    game_rows = []
    for title in games:
        normalized = title.lower()
        game = db.query(Game).filter(Game.normalized_name == normalized).first()
        if not game:
            game = Game(normalized_name=normalized, display_name=title)
            db.add(game)
            db.flush()
        game_rows.append(game)

    now = datetime.now(timezone.utc)
    for day_offset in range(days):
        day = now - timedelta(days=day_offset)
        for user in users:
            if random.random() < 0.55:
                game = random.choice(game_rows)
                start = day.replace(hour=random.randint(16, 22), minute=random.randint(0, 59), second=0, microsecond=0)
                duration_min = random.randint(20, 240)
                end = start + timedelta(minutes=duration_min)
                db.add(
                    ActivitySession(
                        guild_id=guild_id,
                        user_id=user.id,
                        game_id=game.id,
                        started_at=start,
                        ended_at=end,
                        activity_type="playing",
                    )
                )

    for user in users:
        for game in random.sample(game_rows, k=2):
            db.add(
                ManualPlaytime(
                    guild_id=guild_id,
                    user_id=user.id,
                    game_id=game.id,
                    duration_seconds=random.randint(20, 400) * 3600,
                    source=ManualSource.historical,
                    note="Demo historical data",
                )
            )
            db.add(
                PlaytimeAdjustment(
                    guild_id=guild_id,
                    user_id=user.id,
                    game_id=game.id,
                    adjustment_seconds=random.choice([-1, 1]) * random.randint(10, 120) * 60,
                    reason="Demo adjustment",
                )
            )

    db.commit()
