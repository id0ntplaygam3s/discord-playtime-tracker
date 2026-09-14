from __future__ import annotations

import re


def normalize_game_name(name: str) -> str:
    value = name.strip().lower()
    value = re.sub(r"[\u2122\u00ae]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value
