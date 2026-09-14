from __future__ import annotations

import csv
import io
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models import AuditAction, ManualPlaytime, ManualSource, PlaytimeAdjustment
from app.services.playtime import total_seconds_for_user_game
from app.services.session_service import write_audit_log


@dataclass
class ImportRowError:
    row_number: int
    message: str


def to_seconds(hours: int, minutes: int) -> int:
    return (hours * 3600) + (minutes * 60)


def create_manual_playtime(
    db: Session,
    guild_id: int,
    user_id: int,
    game_id: int,
    duration_seconds: int,
    source: ManualSource,
    note: str | None,
    created_by: int,
    commit: bool = True,
) -> ManualPlaytime:
    record = ManualPlaytime(
        guild_id=guild_id,
        user_id=user_id,
        game_id=game_id,
        duration_seconds=duration_seconds,
        source=source,
        note=note,
        created_by=created_by,
    )
    db.add(record)
    if commit:
        db.commit()
        db.refresh(record)
    else:
        db.flush()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.manual_playtime_created,
        admin_user_id=created_by,
        target_user_id=user_id,
        target_game_id=game_id,
        change_seconds=duration_seconds,
        reason=note,
        commit=commit,
    )
    return record


def create_adjustment(
    db: Session,
    guild_id: int,
    user_id: int,
    game_id: int,
    adjustment_seconds: int,
    reason: str,
    created_by: int,
    allow_negative_total: bool = False,
    commit: bool = True,
) -> PlaytimeAdjustment:
    current = total_seconds_for_user_game(db, guild_id, user_id, game_id)
    if not allow_negative_total and current + adjustment_seconds < 0:
        raise ValueError("Adjustment would result in negative total playtime")

    record = PlaytimeAdjustment(
        guild_id=guild_id,
        user_id=user_id,
        game_id=game_id,
        adjustment_seconds=adjustment_seconds,
        reason=reason,
        created_by=created_by,
    )
    db.add(record)
    if commit:
        db.commit()
        db.refresh(record)
    else:
        db.flush()

    write_audit_log(
        db,
        guild_id=guild_id,
        action=AuditAction.adjustment_created,
        admin_user_id=created_by,
        target_user_id=user_id,
        target_game_id=game_id,
        change_seconds=adjustment_seconds,
        reason=reason,
        commit=commit,
    )
    return record


def set_absolute_total(
    db: Session,
    guild_id: int,
    user_id: int,
    game_id: int,
    desired_total_seconds: int,
    reason: str,
    created_by: int,
    commit: bool = True,
) -> PlaytimeAdjustment:
    current = total_seconds_for_user_game(db, guild_id, user_id, game_id)
    delta = desired_total_seconds - current
    return create_adjustment(
        db,
        guild_id=guild_id,
        user_id=user_id,
        game_id=game_id,
        adjustment_seconds=delta,
        reason=reason,
        created_by=created_by,
        allow_negative_total=False,
        commit=commit,
    )


def parse_csv_preview(content: bytes) -> tuple[list[dict], list[ImportRowError]]:
    text_content = content.decode("utf-8")
    reader = csv.DictReader(io.StringIO(text_content))
    rows: list[dict] = []
    errors: list[ImportRowError] = []

    required = {"Discord User", "Game", "Hours", "Minutes", "Source", "Note"}
    if set(reader.fieldnames or []) != required:
        errors.append(ImportRowError(row_number=0, message="Invalid headers"))
        return rows, errors

    for idx, row in enumerate(reader, start=2):
        try:
            hours = int(row["Hours"])
            minutes = int(row["Minutes"])
            source = row["Source"].strip().lower()
            if source not in {"historical", "imported", "correction"}:
                raise ValueError("invalid source")
            if hours < 0 or minutes < 0 or minutes > 59:
                raise ValueError("invalid time")
            rows.append(
                {
                    "discord_user": row["Discord User"].strip(),
                    "game": row["Game"].strip(),
                    "hours": hours,
                    "minutes": minutes,
                    "source": source,
                    "note": row.get("Note", "").strip() or None,
                }
            )
        except Exception as exc:
            errors.append(ImportRowError(row_number=idx, message=str(exc)))

    return rows, errors
