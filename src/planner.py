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
from .claims import check_plan
from .models import Asset, ChannelSlot, JobState, Platform, PublishMode, VideoPlan
from .store import Store


def _seed_for(slot_id: str, day: str, index: int) -> int:
    """Детерминированный seed: один и тот же план на одну дату воспроизводится байт в байт."""
    h = hashlib.sha256(f"{slot_id}|{day}|{index}".encode()).hexdigest()
    return int(h[:12], 16)


def _windows_for(platform: Platform, geo_code: str, arm: str = "A") -> list[str]:
    """Окна постинга в ЛОКАЛЬНОМ времени гео для плеча эксперимента.

    Арм A — прайм-тайм, арм B — окна низкой конкуренции. Смысл в том, что сетка
    каналов служит измерительным инструментом: источники по лучшему времени
    противоречат друг другу сильнее, чем величина самого эффекта, поэтому
    расписание проверяется на своих данных, а не берётся из чужой таблицы.
    """
    sch = schedule()
    slots_local = sch.get("slots_local", {})
    arms = sch.get("experiment_arms", {})
    key = "arm_A_prime" if arm.upper() == "A" else "arm_B_low_competition"
    slot_ids = arms.get(key) or []
    windows = [slots_local[s]["time"] for s in slot_ids if s in slots_local]

    override = (sch.get("by_geo", {}).get(geo_code) or {}).get(platform.value)
    if override:
        windows = override
    if not windows:
        windows = sch.get("defaults", {}).get(platform.value, ["20:00"])
    return windows


def _blackout_bounds(sch: dict) -> tuple[int, int] | None:
    """Границы мёртвой зоны в минутах от полуночи локального времени."""
    bl = sch.get("blackout_local") or {}
    if not bl:
        return None
    def mins(t: str) -> int:
        h, m = (int(x) for x in t.split(":"))
        return h * 60 + m
    return mins(bl.get("from", "02:00")), mins(bl.get("to", "04:59"))


def _to_utc(day: str, local_hhmm: str, tz_name: str) -> str:
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    tz = ZoneInfo(tz_name)
    local_dt = datetime.fromisoformat(day).replace(hour=hh, minute=mm, tzinfo=tz)
    return local_dt.astimezone(timezone.utc).isoformat(timespec="seconds")


def _schedule_time(day: str, local_hhmm: str, tz_name: str, seed: int,
                   max_jitter_minutes: int) -> str:
    """Итоговое время публикации в UTC: окно + джиттер, с выводом из мёртвой зоны.

    Джиттер обязателен: двадцать аккаунтов, публикующих в одну минуту, — самый
    заметный машинный признак. Но джиттер может утащить пост в мёртвую зону
    (02:00-04:59 местного), поэтому проверяется ИТОГОВОЕ время, а не окно.
    """
    tz = ZoneInfo(tz_name)
    hh, mm = (int(x) for x in local_hhmm.split(":"))
    local_dt = datetime.fromisoformat(day).replace(hour=hh, minute=mm, tzinfo=tz)
    if max_jitter_minutes > 0:
        rng = random.Random(seed)
        local_dt += timedelta(minutes=rng.randint(-max_jitter_minutes, max_jitter_minutes))

    bounds = _blackout_bounds(schedule())
    if bounds:
        start, end = bounds
        minute_of_day = local_dt.hour * 60 + local_dt.minute
        if start <= minute_of_day <= end:
            local_dt += timedelta(minutes=end - minute_of_day + 1)
    return local_dt.astimezone(timezone.utc).isoformat(timespec="seconds")


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

    if game:
        # канал про одну игру: хуки про другие игры ломают позиционирование
        tiers = [
            [h for h in pool if fits(h) and game in (h.get("games") or [])],
            [h for h in pool if fits(h) and not h.get("games")],
            [h for h in pool if game in (h.get("games") or []) or not h.get("games")],
            pool,
        ]
    else:
        # канал без привязки к игре (диагностика, бенчмарки, железо, мифы):
        # ему подходят хуки про ЛЮБУЮ игру, и это резко расширяет пул —
        # иначе остаются только шаблоны без упоминания игры, а их мало
        tiers = [
            [h for h in pool if fits(h)],
            pool,
            list(all_hooks),
        ]
    hooks = next((t for t in tiers if t), list(all_hooks))
    by_template: dict[str, list[str]] = {}
    for h in hooks:
        by_template.setdefault(h.get("from_template") or h["text"], []).append(h["text"])
    return tuple(tuple(v) for k, v in sorted(by_template.items()))


def pick_hook(geo_code: str, game: str | None, fmt: dict, seed: int,
              exclude: frozenset[str] = frozenset()) -> str:
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
    # исключаем уже использованные этим слотом: повторяющийся хук на канале —
    # прямой сигнал однотипного контента и для зрителя, и для площадки
    fresh = tuple(tuple(t for t in grp if t not in exclude) for grp in groups)
    fresh = tuple(grp for grp in fresh if grp)
    text = rng.choice(rng.choice(fresh or groups))

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
    lang = geo["content_language"]
    tail_pool = bank.get("caption_tails", {}).get(lang, [""])
    tail = rng.choice(tail_pool)
    # Последняя строка — вопрос: CTA на комментарий даёт +26% комментариев
    # (Metricool 2026), а комментарий сильнее лайка как сигнал вовлечения.
    ask_pool = bank.get("comment_ctas", {}).get(lang) or bank.get("comment_ctas", {}).get("en", [])
    ask = rng.choice(ask_pool) if ask_pool else ""
    parts = [hook.rstrip(".")]
    if tail:
        parts.append(tail)
    if ask:
        parts.append(ask)
    caption = " — ".join(parts)
    title = hook if len(hook) <= 95 else hook[:92] + "..."

    limits = platform_limits().get(slot.platform.value, {})
    blocked = {t.lower().lstrip("#") for t in limits.get("hashtag_blocklist", [])}
    tags = [t for t in (bank.get("hashtags", {}).get(slot.geo)
                        or bank.get("hashtags", {}).get("default", []))
            if t.lower().lstrip("#") not in blocked]
    n = min(len(tags), int(limits.get("recommended_hashtags", 2)))
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
            windows = _windows_for(slot.platform, slot.geo, slot.arm)
            for i in range(cap):
                seed = _seed_for(slot.slot_id, day, i)
                fmt = pick_format(slot, seed)
                seen_for_slot = used_hooks.setdefault(slot.slot_id, set())
                # Валидатор обещаний — обязательный барьер: непроверяемая цифра в
                # хуке стоит дороже, чем выигрыш от громкой формулировки (возвраты,
                # разбор в комментариях, жалобы в платёжку). Не прошло — берём другой хук.
                hook = caption = title = ""
                tags: list[str] = []
                rejected: list[str] = []
                for attempt in range(5):
                    candidate = pick_hook(slot.geo, slot.target_game, fmt, seed + attempt * 104729,
                                          exclude=frozenset(seen_for_slot) | set(rejected))
                    cap_text, ttl, tg = build_caption(slot, candidate, fmt, seed + attempt * 104729)
                    verdict = check_plan(candidate, cap_text, ttl, fmt.get("beats", []),
                                         game=slot.target_game)
                    if verdict.ok:
                        hook, caption, title, tags = candidate, cap_text, ttl, tg
                        break
                    rejected.append(candidate)
                    store.log("warn", "planner.claims",
                              f"{slot.slot_id}: хук отклонён валидатором", verdict.violations[:3])
                if not hook:
                    store.log("error", "planner.claims",
                              f"{slot.slot_id}: не нашёл хук, проходящий валидатор — слот пропущен")
                    continue
                seen_for_slot.add(hook)
                window = windows[i % len(windows)]
                sched = _schedule_time(day, window, geo["timezone"], seed,
                                       int(plat_limit.get("jitter_minutes", 25)))
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
