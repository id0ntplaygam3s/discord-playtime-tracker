from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


@dataclass
class ResolvedRange:
    from_dt: datetime | None
    to_dt: datetime | None
    key: str


def resolve_range(
    range_key: str | None,
    *,
    timezone_name: str,
    custom_from: datetime | None = None,
    custom_to: datetime | None = None,
    now_utc: datetime | None = None,
) -> ResolvedRange:
    key = (range_key or "").strip().lower()
    if key in {"", "all"}:
        return ResolvedRange(from_dt=None, to_dt=None, key="all")

    now_utc = now_utc or datetime.now(timezone.utc)
    tz = ZoneInfo(timezone_name)
    now_local = now_utc.astimezone(tz)

    if key == "custom":
        if (custom_from is None) != (custom_to is None):
            raise ValueError("Custom range requires both from and to timestamps")
        if custom_from is not None and custom_to is not None and custom_from >= custom_to:
            raise ValueError("Custom range requires from < to")
        return ResolvedRange(from_dt=custom_from, to_dt=custom_to, key="custom")

    if key == "ytd":
        start_local = datetime.combine(date(now_local.year, 1, 1), time.min, tzinfo=tz)
        return ResolvedRange(from_dt=start_local.astimezone(timezone.utc), to_dt=now_utc, key=key)

    day_map = {
        "7d": 7,
        "14d": 14,
        "30d": 30,
        "60d": 60,
        "90d": 90,
        "180d": 180,
        "365d": 365,
    }
    if key in day_map:
        from_local = now_local - timedelta(days=day_map[key])
        return ResolvedRange(from_dt=from_local.astimezone(timezone.utc), to_dt=now_utc, key=key)

    raise ValueError(f"Unsupported range key: {range_key}")
