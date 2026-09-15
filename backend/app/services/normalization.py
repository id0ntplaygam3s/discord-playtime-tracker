from __future__ import annotations

import re
import unicodedata


def normalize_game_name(name: str) -> str:
    value = unicodedata.normalize("NFKC", name or "")
    value = value.strip().lower()
    value = re.sub(r"[\u2122\u00ae\u00a9]", "", value)
    value = re.sub(r"[\-_:;,.!\[\](){}]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value
