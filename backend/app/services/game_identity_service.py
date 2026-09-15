from __future__ import annotations

from difflib import SequenceMatcher

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Game, GameAlias, GameMergeSuggestionState, MergeSuggestionStatus
from app.services.normalization import normalize_game_name


def canonical_game_id_expr():
    return func.coalesce(Game.canonical_game_id, Game.id)


def resolve_canonical_game(db: Session, game: Game) -> Game:
    current = game
    seen: set[int] = set()
    while current.canonical_game_id is not None and current.canonical_game_id not in seen:
        seen.add(current.id)
        next_game = db.query(Game).filter(Game.id == current.canonical_game_id).first()
        if next_game is None:
            break
        current = next_game
    return current


def find_game_by_name_or_alias(db: Session, name: str) -> Game | None:
    normalized = normalize_game_name(name)
    game = db.query(Game).filter(Game.normalized_name == normalized).first()
    if game is not None:
        return resolve_canonical_game(db, game)

    alias = db.query(GameAlias).filter(GameAlias.normalized_alias == normalized).first()
    if alias is None:
        return None
    alias_game = db.query(Game).filter(Game.id == alias.game_id).first()
    if alias_game is None:
        return None
    return resolve_canonical_game(db, alias_game)


def add_alias_if_missing(db: Session, canonical_game_id: int, alias_value: str) -> None:
    trimmed = (alias_value or "").strip()
    if not trimmed:
        return
    normalized = normalize_game_name(trimmed)
    row = db.query(GameAlias).filter(GameAlias.normalized_alias == normalized).first()
    if row is not None:
        return
    db.add(GameAlias(game_id=canonical_game_id, alias=trimmed, normalized_alias=normalized))


def current_total_for_game(db: Session, guild_id: int, game_id: int) -> int:
    from app.services.stats_service import ranked_games

    rows = ranked_games(db, guild_id, source="combined", limit=5000)
    for row in rows:
        if int(row["id"]) == int(game_id):
            return int(row["total_seconds"])
    return 0


def suggest_merge_pairs(db: Session, *, limit: int = 50) -> list[dict]:
    games = db.query(Game).filter(Game.is_hidden.is_(False)).order_by(Game.display_name.asc()).all()
    suggestions: list[dict] = []

    ignored_pairs = {
        (row.source_game_id, row.target_game_id)
        for row in db.query(GameMergeSuggestionState)
        .filter(GameMergeSuggestionState.status == MergeSuggestionStatus.ignored)
        .all()
    }

    for idx, left in enumerate(games):
        left_norm = normalize_game_name(left.display_name)
        for right in games[idx + 1 :]:
            if left.id == right.id:
                continue
            pair = (left.id, right.id)
            if pair in ignored_pairs or (right.id, left.id) in ignored_pairs:
                continue

            right_norm = normalize_game_name(right.display_name)
            if not left_norm or not right_norm:
                continue

            confidence = None
            reason = None
            score = 0.0
            if left_norm == right_norm:
                confidence = "high"
                reason = "Exact normalized match"
                score = 1.0
            elif left.discord_application_id and right.discord_application_id and left.discord_application_id == right.discord_application_id:
                confidence = "high"
                reason = "Matching Discord/Steam application ID"
                score = 0.99
            else:
                ratio = SequenceMatcher(a=left_norm, b=right_norm).ratio()
                score = ratio
                if ratio >= 0.93:
                    confidence = "medium"
                    reason = "Very similar normalized names"
                elif ratio >= 0.88:
                    confidence = "low"
                    reason = "Possible typo/spacing variation"

            if confidence is None:
                continue

            canonical = left if len(left_norm) <= len(right_norm) else right
            duplicate = right if canonical.id == left.id else left
            suggestions.append(
                {
                    "source_game_id": duplicate.id,
                    "source_name": duplicate.display_name,
                    "target_game_id": canonical.id,
                    "target_name": canonical.display_name,
                    "confidence": confidence,
                    "reason": reason,
                    "score": round(score, 4),
                }
            )

    suggestions.sort(key=lambda x: (0 if x["confidence"] == "high" else 1, -x["score"], x["source_name"].lower()))
    return suggestions[:limit]
