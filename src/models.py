"""Доменные модели системы авто-залива.

Все сущности намеренно «плоские» и сериализуемые: они грузятся из data/*.json,
складываются в SQLite (src/store.py) и передаются между планировщиком, рендером
и публикаторами без ORM.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Platform(str, Enum):
    TIKTOK = "tiktok"
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"


class PublishMode(str, Enum):
    """Как именно уходит пост. См. SPEC.md -> «Модель публикации».

    API      — полностью автоматом через официальное API площадки (нужен OAuth аккаунта).
    RELAY    — через сторонний планировщик с мульти-аккаунтом (Metricool/Publer/Postiz/...).
    KIT      — система готовит «пост-кит» (файл + тексты + время) и отдаёт человеку/устройству.
    """
    API = "api"
    RELAY = "relay"
    KIT = "kit"


class JobState(str, Enum):
    PLANNED = "planned"
    RENDERED = "rendered"
    QUEUED = "queued"
    PUBLISHED = "published"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"        # площадка ограничила аккаунт
    NEEDS_HUMAN = "needs_human"


@dataclass
class Geo:
    """Гео-профиль. Источник: data/geos.json (заполняется ресерчем)."""
    code: str                          # ISO-подобный ключ: us, uk, sa, id, br...
    name: str
    priority: int                      # 1 = стартовое гео, 3 = позже, 9 = не брать
    content_language: str              # язык текста на экране/подписей
    voiceover_language: str | None
    subtitle_language: str | None
    timezone: str                      # IANA, напр. America/New_York
    top_games: list[str] = field(default_factory=list)
    slang: list[str] = field(default_factory=list)
    price_tier: str = "mid"            # low | mid | high — влияет на оффер
    entry_point: str = "discord"       # discord | site | telegram | dm
    cta_language: str = "en"
    payment_methods: list[str] = field(default_factory=list)
    needs_local_ip: bool = False
    notes: str = ""

    @property
    def is_active(self) -> bool:
        return self.priority <= 3


@dataclass
class ChannelSlot:
    """Слот канала в сетке. 20 слотов на гео на платформу — чтобы каналы не были дублями."""
    slot_id: str                       # us-tt-01
    geo: str
    platform: Platform
    theme: str                         # «Fortnite FPS fixes», «low-end laptop gaming», ...
    target_game: str | None
    content_formats: list[str] = field(default_factory=list)
    handle: str | None = None
    bio: str | None = None
    persona: str = "faceless"          # faceless | voice | face
    posts_per_day: int = 2
    publish_mode: PublishMode = PublishMode.KIT
    attribution_token: str | None = None   # уникальная метка ссылки/инвайта/промокода
    arm: str = "A"                         # плечо эксперимента по таймингу: A = прайм, B = низкая конкуренция
    active: bool = True


@dataclass
class Account:
    """Реальный аккаунт, привязанный к слоту. Секреты тут НЕ хранятся — только ссылки на них."""
    account_id: str
    slot_id: str
    platform: Platform
    username: str
    created_at: str
    credential_ref: str | None = None      # ключ в .env / секрет-сторе
    proxy_ref: str | None = None
    device_ref: str | None = None
    state: str = "warming"                 # warming | active | limited | banned | retired
    daily_cap: int = 2
    notes: str = ""


@dataclass
class Asset:
    """Исходник: клип геймплея, бенчмарк-запись, скриншот, аудио."""
    asset_id: str
    path: str
    kind: str                              # gameplay | benchmark | screen | broll | audio | music
    game: str | None = None
    duration_s: float | None = None
    tags: list[str] = field(default_factory=list)
    rights: str = "own"                    # own | licensed | ugc_permission
    used_count: int = 0


@dataclass
class VideoPlan:
    """Замысел одного видео до рендера. Именно здесь обеспечивается уникальность."""
    plan_id: str
    slot_id: str
    geo: str
    platform: Platform
    format_id: str                         # ключ из data/content_bank.json
    hook_text: str
    body_beats: list[str] = field(default_factory=list)
    cta_text: str = ""
    caption: str = ""
    title: str = ""
    hashtags: list[str] = field(default_factory=list)
    asset_ids: list[str] = field(default_factory=list)
    audio_asset_id: str | None = None
    variant_seed: int = 0                  # управляет монтажом/шрифтом/темпом
    target_duration_s: float = 18.0
    scheduled_for_utc: str | None = None
    state: JobState = JobState.PLANNED

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["platform"] = self.platform.value
        d["state"] = self.state.value
        return d


@dataclass
class RenderResult:
    plan_id: str
    video_path: str
    thumb_path: str | None
    duration_s: float
    width: int
    height: int
    checksum: str
    rendered_at: str


@dataclass
class PostResult:
    plan_id: str
    account_id: str
    platform: Platform
    state: JobState
    remote_id: str | None = None
    remote_url: str | None = None
    error: str | None = None
    published_at: str | None = None
    mode: PublishMode = PublishMode.KIT


@dataclass
class MetricSnapshot:
    """Снимок метрик поста. Копится по дням — по нему принимаются решения (см. planner)."""
    plan_id: str
    account_id: str
    platform: Platform
    captured_at: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    saves: int = 0
    avg_watch_s: float | None = None
    completion_rate: float | None = None
    profile_views: int | None = None
    link_clicks: int | None = None
    geo_breakdown: dict[str, float] = field(default_factory=dict)   # {"US": 0.62, "IN": 0.11}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
