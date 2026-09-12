"""Планировщик: решает ЧТО, КУДА и КОГДА публиковать.

Три задачи:
1. Разложить план публикаций на N дней по слотам с соблюдением окон постинга и лимитов.
2. Собрать замысел каждого видео (формат, хук, ассеты, подпись) так, чтобы посты
   не превращались в дубли друг друга.
3. По накопленным метрикам сказать, какие слоты масштабировать, а какие закрывать.
"""
from __future__ import annotations

import hashlib
import random
from functools import lru_cache
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from .config import (channel_grid, content_bank, geos, load_json, offers,
                     platform_limits, schedule, settings)
from .models import Asset, ChannelSlot, JobState, Platform, PublishMode, VideoPlan
from .store import Store


def _seed_for(slot_id: str, day: str, index: int) -> int:
    """Детерминированный seed: один и тот же план на одну дату воспроизводится байт в байт."""
    h = hashlib.sha256(f"{slot_id}|{day}|{index}".encode()).hexdigest()
    return int(h[:12], 16)


def _windows_for(platform: Platform, geo_code: str) -> list[str]:
    """Окна постинга в ЛОКАЛЬНОМ времени гео: ["18:30", "21:00"]."""
    sch = schedule()
    by_geo = sch.get("by_geo", {}).get(geo_code, {})
    windows = by_geo.get(platform.value)
    if windows:
        return windows
    return sch.get("defaults", {}).get(platform.value, ["18:00"])


def _to_utc(day: str, local_hhmm: str, tz_name: str) -> str:
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    tz = ZoneInfo(tz_name)
    local_dt = datetime.fromisoformat(day).replace(hour=hh, minute=mm, tzinfo=tz)
    return local_dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _jitter(iso_utc: str, seed: int, max_minutes: int) -> str:
    """Разброс времени: одинаковые минуты на 20 аккаунтах — самый заметный машинный признак."""
    if max_minutes <= 0:
        return iso_utc
    rng = random.Random(seed)
    delta = rng.randint(-max_minutes, max_minutes)
    dt = datetime.fromisoformat(iso_utc) + timedelta(minutes=delta)
    return dt.isoformat(timespec="seconds")


def pick_format(slot: ChannelSlot, seed: int) -> dict:
    bank = content_bank()
    allowed = slot.content_formats or [f["id"] for f in bank["formats"]]
    pool = [f for f in bank["formats"] if f["id"] in allowed]
    if not pool:
        pool = bank["formats"]
    rng = random.Random(seed)
    return rng.choice(pool)


@lru_cache(maxsize=1)
def _hook_pool() -> tuple[dict, ...]:
    """Расширенный банк (тысячи готовых хуков), если он сгенерирован; иначе шаблоны.

    Кешируется: файл на пару мегабайт, а вызовов — по числу планируемых видео.
    """
    try:
        expanded = load_json("hooks_expanded.json").get("hooks", [])
        if expanded:
            return tuple(expanded)
    except FileNotFoundError:
        pass
    return tuple(content_bank()["hooks"])


@lru_cache(maxsize=4096)
def _hook_index(geo_code: str, game: str | None, format_id: str) -> tuple[tuple[str, ...], ...]:
    """Готовые группы хуков по шаблонам для комбинации (гео, игра, формат).

    Возвращает кортеж групп: каждая группа — варианты одного шаблона. Группировка
    считается один раз на комбинацию, а не на каждое видео.
    """
    all_hooks = _hook_pool()
    lang = geos()[geo_code]["content_language"]
    pool = [h for h in all_hooks if h.get("geo") == geo_code] or \
           [h for h in all_hooks if h.get("lang") == lang]

    def fits(h: dict) -> bool:
        return not h.get("formats") or format_id in h["formats"]

    tiers = [
        [h for h in pool if fits(h) and game and game in (h.get("games") or [])],
        [h for h in pool if fits(h) and not h.get("games")],
        [h for h in pool if not h.get("games")],
        pool,
        [h for h in all_hooks if not h.get("games")],
    ]
    hooks = next((t for t in tiers if t), list(all_hooks))
    by_template: dict[str, list[str]] = {}
    for h in hooks:
        by_template.setdefault(h.get("from_template") or h["text"], []).append(h["text"])
    return tuple(tuple(v) for k, v in sorted(by_template.items()))


def pick_hook(geo_code: str, game: str | None, fmt: dict, seed: int) -> str:
    """Хук под язык гео, формат и игру слота.

    Если слот заявлен как канал про одну игру, хук про другую игру ломает
    позиционирование и режет удержание — поэтому фильтр по игре жёсткий.
    Выбор двухшаговый: сначала шаблон, потом вариант внутри него, иначе шаблон
    с двумя числами даёт сотни вариантов и вытесняет остальные.
    """
    groups = _hook_index(geo_code, game, fmt["id"])
    if not groups:
        return ""
    rng = random.Random(seed)
    text = rng.choice(rng.choice(groups))

    bank = content_bank()
    geo = geos()[geo_code]
    repl = {
        "{game}": game or (geo["top_games"][0] if geo.get("top_games") else "your game"),
        "{fps2}": str(rng.choice([f for f in bank.get("fps_claims", [60]) if f > 60] or [120])),
        "{fps}": str(rng.choice(bank.get("fps_claims", [30, 40, 60, 80]))),
        "{slang}": rng.choice(geo["slang"]) if geo.get("slang") else "",
        "{gpu}": rng.choice(bank.get("gpus", ["GTX 1650"])),
    }
    for k, v in repl.items():
        text = text.replace(k, str(v))
    return text.strip()


def build_caption(slot: ChannelSlot, hook: str, fmt: dict, seed: int) -> tuple[str, str, list[str]]:
    bank = content_bank()
    geo = geos()[slot.geo]
    off = offers().get("by_price_tier", {}).get(geo.get("price_tier", "mid"), {})
    rng = random.Random(seed)
    cta_pool = off.get("cta", bank.get("cta", ["link in bio"]))
    cta = rng.choice(cta_pool)
    tail_pool = bank.get("caption_tails", {}).get(geo["content_language"], [""])
    tail = rng.choice(tail_pool)
    caption = f"{hook.rstrip('.')} — {tail}".strip(" —") if tail else hook
    title = hook if len(hook) <= 95 else hook[:92] + "..."
    tags = bank.get("hashtags", {}).get(slot.geo) or bank.get("hashtags", {}).get("default", [])
    n = min(len(tags), platform_limits().get(slot.platform.value, {}).get("recommended_hashtags", 4))
    return caption, title, rng.sample(tags, n) if n else []


VISUAL_KINDS = ("gameplay", "benchmark", "screen", "broll")


def choose_assets(store: Store, slot: ChannelSlot, fmt: dict, pool: list[Asset], seed: int) -> list[str]:
    """Выбор ВИЗУАЛЬНЫХ ассетов под видео.

    Приоритет: свежие клипы нужной игры -> любые клипы нужной игры -> нейтральный
    визуал (b-roll/бенчмарки/экран) -> любой визуал. Аудио сюда не попадает никогда:
    музыка подставляется отдельно в cli.cmd_render.
    """
    rng = random.Random(seed)
    need = int(fmt.get("clips_needed", 2))
    game = slot.target_game
    visual = [a for a in pool if a.kind in VISUAL_KINDS]

    tiers = [
        [a for a in visual
         if (not game or a.game == game)
         and not store.asset_used_by_slot(a.asset_id, slot.slot_id)],
        [a for a in visual if not game or a.game == game],
        [a for a in visual if a.kind in ("broll", "screen", "benchmark")],
        visual,
    ]
    for candidates in tiers:
        if len(candidates) >= need:
            picked = list(candidates)
            rng.shuffle(picked)
            return [a.asset_id for a in picked[:need]]

    # визуала меньше, чем просит формат: отдаём что есть, рендер переиспользует клип
    picked = list(visual)
    rng.shuffle(picked)
    return [a.asset_id for a in picked] or []


def plan_days(store: Store, assets: list[Asset], days: int = 7,
              start: datetime | None = None,
              geo_filter: list[str] | None = None) -> list[VideoPlan]:
    """Главная точка входа: строит план публикаций на `days` дней вперёд."""
    cfg = settings()
    start = start or datetime.now(timezone.utc)
    plans: list[VideoPlan] = []
    limits = platform_limits()
    # история хуков в рамках одного прогона планирования: канал не должен повторять
    # одну и ту же фразу через день — это заметно и зрителю, и площадке
    used_hooks: dict[str, set[str]] = {}

    for d in range(days):
        day = (start + timedelta(days=d)).date().isoformat()
        for slot in store.slots():
            if geo_filter and slot.geo not in geo_filter:
                continue
            geo = geos().get(slot.geo)
            if not geo or geo.get("priority", 9) > 3:
                continue
            acct = store.account_for_slot(slot.slot_id)
            plat_limit = limits.get(slot.platform.value, {})
            hard_cap = int(plat_limit.get("max_posts_per_day", 3))
            warming_cap = int(plat_limit.get("warming_posts_per_day", 1))
            cap = min(slot.posts_per_day, hard_cap)
            if acct and acct.state == "warming":
                cap = min(cap, warming_cap)
            windows = _windows_for(slot.platform, slot.geo)
            for i in range(cap):
                seed = _seed_for(slot.slot_id, day, i)
                fmt = pick_format(slot, seed)
                seen_for_slot = used_hooks.setdefault(slot.slot_id, set())
                hook = ""
                for attempt in range(6):
                    fmt = pick_format(slot, seed + attempt * 7919)
                    hook = pick_hook(slot.geo, slot.target_game, fmt, seed + attempt * 7919)
                    if hook not in seen_for_slot:
                        break
                seen_for_slot.add(hook)
                caption, title, tags = build_caption(slot, hook, fmt, seed)
                window = windows[i % len(windows)]
                sched = _jitter(
                    _to_utc(day, window, geo["timezone"]),
                    seed,
                    int(plat_limit.get("jitter_minutes", 25)),
                )
                plan = VideoPlan(
                    plan_id=f"{slot.slot_id}-{day}-{i}",
                    slot_id=slot.slot_id,
                    geo=slot.geo,
                    platform=slot.platform,
                    format_id=fmt["id"],
                    hook_text=hook,
                    body_beats=fmt.get("beats", []),
                    cta_text=offers().get("by_price_tier", {})
                        .get(geo.get("price_tier", "mid"), {})
                        .get("primary_cta", "link in bio"),
                    caption=caption,
                    title=title,
                    hashtags=tags,
                    asset_ids=choose_assets(store, slot, fmt, assets, seed),
                    variant_seed=seed,
                    target_duration_s=float(fmt.get("duration_s", 18)),
                    scheduled_for_utc=sched,
                    state=JobState.PLANNED,
                )
                plans.append(plan)
                store.save_plan(plan)
    store.log("info", "planner", f"построено планов: {len(plans)}", {"days": days})
    return plans


# ---------- решения по слотам ----------

def review_slots(store: Store, days: int = 14) -> dict[str, list[dict]]:
    """Сортирует слоты на «масштабировать / оставить / закрыть» по порогам из data/schedule.json."""
    th = schedule().get("decision_thresholds", {})
    min_views = int(th.get("min_median_views_2w", 500))
    kill_views = int(th.get("kill_below_views_2w", 150))
    min_posts = int(th.get("min_posts_before_verdict", 20))
    scale_views = int(th.get("scale_above_views_2w", 5000))

    out: dict[str, list[dict]] = {"scale": [], "keep": [], "kill": [], "too_early": []}
    for row in store.slot_performance(days=days):
        posts = row.get("posts") or 0
        views = row.get("views") or 0
        rev = row.get("revenue_usd") or 0
        bucket = "keep"
        if posts < min_posts:
            bucket = "too_early"
        elif rev > 0 or views >= scale_views:
            bucket = "scale"
        elif views < kill_views:
            bucket = "kill"
        elif views < min_views:
            bucket = "keep"
        out[bucket].append(row)
    return out
