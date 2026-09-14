from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

STEAM_API_BASE = "https://api.steampowered.com"


@dataclass
class SteamOwnedGame:
    appid: int
    name: str
    playtime_minutes: int


@dataclass
class SteamImportPreview:
    steam_id: str
    profile_label: str
    games: list[SteamOwnedGame]


def _extract_vanity_from_url(profile: str) -> str | None:
    parsed = urlparse(profile)
    path = parsed.path.strip("/")
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"id", "profiles"}:
        return parts[1]
    return None


def resolve_steam_id(profile: str, steam_api_key: str, timeout_seconds: int = 20) -> tuple[str, str]:
    value = profile.strip()
    if not value:
        raise ValueError("Steam profile is required")

    if value.isdigit() and len(value) >= 16:
        return value, value

    vanity = _extract_vanity_from_url(value)
    if vanity is None:
        vanity = re.sub(r"^https?://", "", value, flags=re.IGNORECASE).strip("/")

    if not vanity:
        raise ValueError("Unable to parse Steam vanity/profile identifier")

    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.get(
            f"{STEAM_API_BASE}/ISteamUser/ResolveVanityURL/v1/",
            params={"key": steam_api_key, "vanityurl": vanity},
        )
        resp.raise_for_status()
        data = resp.json().get("response", {})

    if int(data.get("success", 0)) != 1 or not data.get("steamid"):
        raise ValueError("Steam profile not found or not resolvable")

    return str(data["steamid"]), vanity


def fetch_steam_owned_games(profile: str, steam_api_key: str, timeout_seconds: int = 20) -> SteamImportPreview:
    if not steam_api_key:
        raise ValueError("STEAM_API_KEY is required for Steam imports")

    steam_id, label = resolve_steam_id(profile, steam_api_key, timeout_seconds=timeout_seconds)

    with httpx.Client(timeout=timeout_seconds) as client:
        resp = client.get(
            f"{STEAM_API_BASE}/IPlayerService/GetOwnedGames/v1/",
            params={
                "key": steam_api_key,
                "steamid": steam_id,
                "include_appinfo": 1,
                "include_played_free_games": 1,
            },
        )
        resp.raise_for_status()
        payload = resp.json().get("response", {})

    games: list[SteamOwnedGame] = []
    for item in payload.get("games", []):
        minutes = int(item.get("playtime_forever", 0))
        if minutes <= 0:
            continue
        appid = int(item.get("appid", 0))
        if appid <= 0:
            continue
        name = str(item.get("name") or f"Steam App {appid}").strip()
        games.append(SteamOwnedGame(appid=appid, name=name, playtime_minutes=minutes))

    games.sort(key=lambda g: g.playtime_minutes, reverse=True)
    return SteamImportPreview(steam_id=steam_id, profile_label=label, games=games)
