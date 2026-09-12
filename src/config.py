"""Загрузка конфигов и данных. Ничего не хардкодим в коде — всё в data/*.json и .env."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def load_json(name: str) -> Any:
    path = DATA / name
    if not path.exists():
        raise FileNotFoundError(
            f"{path} не найден. Файлы data/*.json — источник истины для стратегии; "
            f"см. SPEC.md, раздел «Слой данных»."
        )
    with path.open(encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=None)
def geos() -> dict[str, dict]:
    return {g["code"]: g for g in load_json("geos.json")["geos"]}


@lru_cache(maxsize=None)
def schedule() -> dict:
    return load_json("schedule.json")


@lru_cache(maxsize=None)
def platform_limits() -> dict:
    return load_json("platform_limits.json")


@lru_cache(maxsize=None)
def content_bank() -> dict:
    return load_json("content_bank.json")


@lru_cache(maxsize=None)
def channel_grid() -> dict:
    return load_json("channels.json")


@lru_cache(maxsize=None)
def offers() -> dict:
    return load_json("offers.json")


@dataclass
class Settings:
    """Рантайм-настройки. Секреты только из окружения, в репозиторий не попадают."""
    state_db: str = os.getenv("STATE_DB", str(ROOT / "state.db"))
    out_dir: str = os.getenv("OUT_DIR", str(ROOT / "out"))
    assets_dir: str = os.getenv("ASSETS_DIR", str(ROOT / "assets"))
    ffmpeg: str = os.getenv("FFMPEG_BIN", "ffmpeg")
    ffprobe: str = os.getenv("FFPROBE_BIN", "ffprobe")
    dry_run: bool = os.getenv("DRY_RUN", "1") == "1"
    relay_provider: str = os.getenv("RELAY_PROVIDER", "")      # metricool | publer | postiz | ...
    relay_api_key: str = os.getenv("RELAY_API_KEY", "")
    link_base: str = os.getenv("LINK_BASE", "https://example.com/go")
    discord_invite_base: str = os.getenv("DISCORD_INVITE_BASE", "")

    def limit(self, platform: str, key: str, default: Any = None) -> Any:
        return platform_limits().get(platform, {}).get(key, default)


@lru_cache(maxsize=None)
def settings() -> Settings:
    return Settings()
