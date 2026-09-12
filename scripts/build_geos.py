#!/usr/bin/env python3
"""Собирает data/geos.json и docs/02-geo-playbooks.md из отчётов ресерча.

Запускать повторно по мере готовности страновых агентов: скрипт идемпотентен и
перезаписывает оба файла целиком из research/raw/geo__*.json.

Зачем отдельный шаг: агенты возвращают богатую, но неоднородную структуру, а
планировщику нужен узкий машинный контракт (язык, таймзона, игры, цена, точка
приёма). Здесь происходит нормализация, а не переписывание смысла.
"""
from __future__ import annotations

import glob
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "research" / "raw"

# Таймзона — единственное, чего нет в отчётах агентов; IANA обязательна из-за DST.
TZ = {
    "us": "America/New_York", "ca": "America/Toronto", "uk": "Europe/London",
    "de": "Europe/Berlin", "fr": "Europe/Paris", "es": "Europe/Madrid",
    "it": "Europe/Rome", "pl": "Europe/Warsaw", "nl_be": "Europe/Amsterdam",
    "nordics": "Europe/Stockholm", "cee": "Europe/Bucharest", "tr": "Europe/Istanbul",
    "au_nz": "Australia/Sydney", "pt_gr": "Europe/Lisbon",
    "sa": "Asia/Riyadh", "ae": "Asia/Dubai", "eg": "Africa/Cairo", "iq": "Asia/Baghdad",
    "maghreb": "Africa/Casablanca", "gulf_small": "Asia/Kuwait",
    "id": "Asia/Jakarta", "ph": "Asia/Manila", "vn": "Asia/Ho_Chi_Minh",
    "th_my": "Asia/Bangkok", "in": "Asia/Kolkata", "jp": "Asia/Tokyo", "kr": "Asia/Seoul",
    "ng": "Africa/Lagos", "ke_tz": "Africa/Nairobi", "za": "Africa/Johannesburg",
    "af_fr": "Africa/Abidjan",
    "ru": "Europe/Moscow", "kz_uz": "Asia/Almaty", "ua_by": "Europe/Kyiv",
    "br": "America/Sao_Paulo", "mx": "America/Mexico_City",
}

LANG_FALLBACK = {
    "us": "en", "ca": "en", "uk": "en", "au_nz": "en", "nl_be": "en", "nordics": "en",
    "de": "de", "fr": "fr", "es": "es", "it": "it", "pl": "pl", "cee": "en", "tr": "tr",
    "pt_gr": "pt", "sa": "ar", "ae": "ar", "eg": "ar", "iq": "ar", "maghreb": "ar",
    "gulf_small": "ar", "id": "id", "ph": "en", "vn": "vi", "th_my": "th", "in": "hi",
    "jp": "ja", "kr": "ko", "ng": "en", "ke_tz": "en", "za": "en", "af_fr": "fr",
    "ru": "ru", "kz_uz": "ru", "ua_by": "ru", "br": "pt", "mx": "es",
}

VERDICT_TO_PRIORITY = {"priority_1": 1, "priority_2": 2, "priority_3": 3, "skip": 9}

# Страны, которым платёжные системы не дают платить (data/payments.json).
# Лить на них показы бессмысленно: аудитория есть, оплатить не может.
BLOCKED_BUYERS = {"cf","cu","kp","cd","er","gw","ir","iq","lb","ly","ml","ru","so","ss","sd","sy","ye"}


def _clean_slang(items: list) -> list[str]:
    """Достаёт из отчёта короткие сленговые слова, отбрасывая пояснения.

    Агенты возвращают сленг с доказательствами: "beauty / what a beauty (EN-CA,
    ПОДТВЕРЖДЕНО: Contiki, Narcity...)". В хук должно попасть только само слово,
    иначе подстановка {slang} втащит в подпись абзац ресерча.
    """
    out: list[str] = []
    for raw in items or []:
        t = str(raw).strip()
        if not t:
            continue
        t = re.split(r"[(\[—:]|\s[-–]\s", t)[0]          # отрезаем пояснение
        t = t.split("/")[0].strip().strip('"\'«»')         # берём первый вариант
        if not t or len(t) > 24:
            continue
        if len(t.split()) > 3:
            continue
        if re.search(r"(?i)подтвержд|источник|confirm|см\.", t):
            continue
        if t.lower() not in (x.lower() for x in out):
            out.append(t)
    return out[:15]


LANG_KEYS = [
    ("ar", ("arabic", "араб")), ("en", ("english", "англ")),
    ("es", ("spanish", "испан", "castellano")), ("pt", ("portug", "португ")),
    ("de", ("german", "немец")), ("fr", ("french", "француз")),
    ("id", ("indonesi", "индонез", "bahasa")), ("tr", ("turkish", "турец")),
    ("vi", ("vietnam", "вьетнам")), ("th", ("thai", "тайск")),
    ("hi", ("hindi", "хинди")), ("ja", ("japan", "япон")), ("ko", ("korea", "корей")),
    ("ru", ("russian", "русск")), ("it", ("italian", "итальян")), ("pl", ("polish", "поль")),
]


def _lang_code(raw: str | None, geo: str) -> str:
    """Код языка контента из описания агента.

    Берём язык, упомянутый РАНЬШЕ всех в тексте, а не первый из нашего списка.
    Отчёт по Саудовской Аравии начинается словом «Арабский», но дальше содержит
    «только 12% на английском» — наивная проверка по порядку списка давала английский
    и уводила всё гео на неверный язык контента.
    """
    if not raw:
        return LANG_FALLBACK.get(geo, "en")
    t = str(raw).lower()
    hits = []
    for code, keys in LANG_KEYS:
        for k in keys:
            i = t.find(k)
            if i >= 0:
                hits.append((i, code))
                break
    return min(hits)[1] if hits else LANG_FALLBACK.get(geo, "en")


def _clean_game(raw: str) -> str:
    """Название игры из отчёта: агенты пишут его с пояснениями и переводами.

    'PUBG Mobile (ببجي موبايل) — включая игру на ЭМУЛЯТОРЕ на ПК' -> 'PUBG Mobile'.
    Без этого пояснительная проза попадала прямо в текст хука на экране.
    """
    t = re.split(r"[(\[]|\s—|\s-\s|,", str(raw))[0]
    t = t.split("/")[0].strip()
    return t if t and len(t) <= 30 and len(t.split()) <= 5 else ""


def _price_tier(mon: dict) -> tuple[str, list[float]]:
    """Ценовой тир по МЕСЯЧНОЙ цене подписки.

    Отчёты агентов описывают прайс прозой ("Месяц: $2.5-3.5 (129-180 EGP)...
    LIFETIME: $12-15"), поэтому нельзя просто собрать все числа: в текст попадают
    курс валюты, локальные суммы и цена lifetime, и дешёвое гео уезжает в high.
    Берём числа только из фрагмента про месяц.
    """
    text = str(mon.get("recommended_price_usd") or "") + " " + str(mon.get("willingness_to_pay") or "")
    if not text.strip():
        return "mid", []

    # фрагмент от упоминания месяца до следующего SKU (3 месяца / год / lifetime)
    m = re.search(r"(мес[а-я]*|month|monthly)\s*[:\-—]?(.{0,120})", text, re.IGNORECASE | re.DOTALL)
    window = m.group(2) if m else text[:120]
    window = re.split(r"(3\s*мес|кварт|год|year|lifetime|навсегда)", window, flags=re.IGNORECASE)[0]

    # только суммы в долларах: $9.99, 2,00 USD, $2.5-3.5
    nums = [float(x.replace(",", ".")) for x in
            re.findall(r"\$\s?(\d{1,2}(?:[.,]\d{1,2})?)|(?<![\d.,])(\d{1,2}(?:[.,]\d{1,2})?)\s*(?:USD|usd|\$)",
                       window) for x in ([x] if isinstance(x, str) else x) if x]
    monthly = [n for n in nums if 0.5 <= n <= 30]
    if not monthly:
        return "mid", []
    base = sum(monthly) / len(monthly)
    tier = "high" if base >= 8 else ("mid" if base >= 4 else "low")
    return tier, sorted(set(monthly))[:6]


def _entry_point(funnel: dict) -> str:
    """Куда вести трафик в этом гео.

    Ищем, что упомянуто РАНЬШЕ в описании воронки, а не что раньше стоит в нашем
    списке: отчёт вида "ГЛАВНЫЙ ВХОД: WhatsApp (а не Discord, потому что...)"
    при наивном порядке проверок давал Discord.
    """
    t = str(funnel.get("entry_point") or "").lower()
    if not t:
        return "discord"
    aliases = {
        "discord": ("discord", "дискорд"),
        "telegram": ("telegram", "телеграм"),
        "whatsapp": ("whatsapp", "вотсап", "ватсап"),
        "site": ("site", "сайт", "лендинг", "landing", ".gg домен", "домен"),
        "dm": ("dm", "личк", "direct message"),
    }
    hits = []
    for target, keys in aliases.items():
        for k in keys:
            i = t.find(k)
            if i >= 0:
                hits.append((i, target))
                break
    return min(hits)[1] if hits else "discord"


def _compact(text: str, limit: int = 40) -> str:
    """Короткое значение для сводной таблицы: отчёты пишут прозой, в таблицу нужна суть."""
    t = " ".join(str(text).split())
    t = t.replace("|", "/")
    return (t[:limit] + "…") if len(t) > limit else t


def _first_money(text: str) -> str:
    """Первая долларовая сумма из прозы про цены."""
    m = re.search(r"\$\s?\d{1,2}(?:[.,]\d{1,2})?(?:\s?[-–]\s?\$?\d{1,2}(?:[.,]\d{1,2})?)?", str(text))
    if m:
        return m.group(0)
    m = re.search(r"\d{1,2}(?:[.,]\d{1,2})?\s*USD", str(text))
    return m.group(0) if m else "?"


def _needs_local_ip(pg: dict) -> bool:
    t = str(pg.get("need_local_ip") or "").lower()
    negative = ("не нужен", "не требуется", "нет", "not needed", "no ", "false",
                "не обязателен", "не критич", "необязателен")
    positive = ("нужен", "обязателен", "требуется", "yes", "true", "критичен")
    if any(n in t for n in negative):
        return False
    return any(pos in t for pos in positive)


def load_overrides() -> dict[str, dict]:
    p = ROOT / "data" / "geo_overrides.json"
    if not p.exists():
        return {}
    return {k: v for k, v in json.loads(p.read_text(encoding="utf-8")).items()
            if not k.startswith("_")}


def load_reports() -> dict[str, dict]:
    out = {}
    for f in sorted(glob.glob(str(RAW / "geo__*.json"))):
        code = Path(f).stem.replace("geo__", "")
        try:
            out[code] = json.loads(Path(f).read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            print(f"  пропуск {code}: битый JSON ({e})")
    return out


def build_geos(reports: dict[str, dict]) -> dict:
    overrides = load_overrides()
    geos = []
    for code, r in sorted(reports.items(), key=lambda kv: (
            VERDICT_TO_PRIORITY.get(kv[1].get("verdict", ""), 9), kv[0])):
        lang = r.get("language") or {}
        mon = r.get("monetization") or {}
        tier, prices = _price_tier(mon)
        content_lang = _lang_code(lang.get("primary_content_language"), code)
        games = [_clean_game(g.get("game")) for g in (r.get("top_games") or []) if g.get("game")]
        games = [g for g in games if g]
        slang = _clean_slang(lang.get("slang_terms") or [])
        codes = {str(c).lower() for c in (r.get("country_codes") or [])} | {code}
        payment_blocked = bool(codes & BLOCKED_BUYERS)
        priority = VERDICT_TO_PRIORITY.get(r.get("verdict", ""), 9)
        if payment_blocked:
            priority = max(priority, 3)
        geos.append({
            "code": code,
            "name": r.get("country") or code,
            "priority": priority,
            "payment_blocked": payment_blocked,
            "verdict_reason": (r.get("verdict_reason") or "")[:600],
            "content_language": content_lang,
            "voiceover_language": _lang_code(lang.get("voiceover_recommendation"), code),
            "subtitle_language": _lang_code(lang.get("subtitle_language"), code),
            "english_works": (lang.get("english_works") or "")[:300],
            "timezone": TZ.get(code, "UTC"),
            "top_games": games[:12],
            "slang": slang,
            "price_tier": tier,
            "price_points_usd": prices,
            "entry_point": _entry_point(r.get("funnel") or {}),
            "cta_language": content_lang,
            "payment_methods": [p for p in (mon.get("payment_methods") or []) if p][:10],
            "needs_local_ip": _needs_local_ip(r.get("proxy_and_account_geo") or {}),
            "notes": (r.get("verdict_reason") or "")[:300],
        })
        # ручные поправки применяются последними: они выражают решения, которые
        # из отчёта автоматически не выводятся
        if code in overrides:
            geos[-1].update({k: v for k, v in overrides[code].items() if not k.startswith("_")})
    return {
        "_meta": {
            "purpose": "Гео-профили: язык, игры, сленг, цена, точка приёма, таймзона.",
            "source": "собрано scripts/build_geos.py из отчётов страновых агентов",
            "priority": "1 = стартовое гео, 2 = второй эшелон, 3 = третий, 9 = не брать (planner игнорирует > 3)",
            "countries": len(geos),
            "overrides_applied": sorted(set(overrides) & {g["code"] for g in geos}),
            "needs_local_ip_note": "Гранулярность органической гео-выдачи = страна; город IP влияния не имеет. Поле означает только необходимость страново-корректного IP, не города.",
        },
        "geos": geos,
    }


def build_playbooks(reports: dict[str, dict]) -> str:
    order = sorted(reports.items(), key=lambda kv: (
        VERDICT_TO_PRIORITY.get(kv[1].get("verdict", ""), 9), kv[0]))
    L = ["# Страновые схемы работы с трафиком", "",
         "Источник: страновые агенты ресерча. Для каждой страны — вердикт с обоснованием,",
         "язык контента, топ-игры, цены, площадки, тайминги, план каналов, идеи контента,",
         "воронка, конкуренция, гео-техника, KPI и риски.", "",
         f"Готово стран: **{len(order)}**", "",
         "| Страна | Приоритет | Язык | Топ-3 игры | Цена/мес | Точка приёма |",
         "|---|---|---|---|---|---|"]
    for code, r in order:
        mon = r.get("monetization") or {}
        tier, _ = _price_tier(mon)
        games = ", ".join(str(g.get("game", "")).split("(")[0].strip()
                          for g in (r.get("top_games") or [])[:3])
        L.append(f"| `{code}` {_compact(r.get('country', code), 34)} | {r.get('verdict', '?')} | "
                 f"{_lang_code((r.get('language') or {}).get('primary_content_language'), code)} | "
                 f"{_compact(games, 42)} | {_first_money(mon.get('recommended_price_usd'))} ({tier}) | "
                 f"{_entry_point(r.get('funnel') or {})} |")
    L.append("")

    for code, r in order:
        L += ["---", "", f"## {r.get('country', code)} (`{code}`)", "",
              f"**Вердикт:** {r.get('verdict', '?')} — {r.get('verdict_reason', '')}", ""]

        aud = r.get("audience") or {}
        if aud:
            L.append("### Аудитория")
            for k, v in aud.items():
                if v and not k.startswith("_"):
                    L.append(f"- **{k}**: {v}")
            L.append("")

        lang = r.get("language") or {}
        if lang:
            L.append("### Язык контента")
            for k in ("primary_content_language", "english_works", "subtitle_language",
                      "voiceover_recommendation", "notes"):
                if lang.get(k):
                    L.append(f"- **{k}**: {lang[k]}")
            if lang.get("slang_terms"):
                L.append(f"- **сленг для хуков**: {', '.join(str(x) for x in lang['slang_terms'])}")
            L.append("")

        if r.get("top_games"):
            L += ["### Топ-игры", "", "| Игра | Популярность | Боль по FPS | Почему подходит офферу |",
                  "|---|---|---|---|"]
            for g in r["top_games"][:12]:
                L.append(f"| {g.get('game','')} | {str(g.get('popularity_note',''))[:150]} | "
                         f"{str(g.get('fps_pain_level',''))[:80]} | {str(g.get('why_good_for_offer',''))[:150]} |")
            L.append("")

        mon = r.get("monetization") or {}
        if mon:
            L.append("### Деньги")
            for k, v in mon.items():
                if v and not k.startswith("_"):
                    L.append(f"- **{k}**: {v if not isinstance(v, list) else ', '.join(map(str, v))}")
            L.append("")

        if r.get("platforms"):
            L += ["### Площадки", "", "| Площадка | Приоритет | Органический охват | Локальные особенности | Ограничения |",
                  "|---|---|---|---|---|"]
            for p in r["platforms"]:
                L.append(f"| {p.get('platform','')} | {p.get('priority','')} | "
                         f"{str(p.get('organic_reach_note',''))[:160]} | "
                         f"{str(p.get('local_specifics',''))[:160]} | {str(p.get('restrictions',''))[:120]} |")
            L.append("")

        if r.get("posting_schedule"):
            L += ["### Тайминги", "", "| Площадка | Дни | Местное время | UTC | Постов/день | Обоснование |",
                  "|---|---|---|---|---|---|"]
            for s in r["posting_schedule"]:
                L.append(f"| {s.get('platform','')} | {str(s.get('days',''))[:40]} | "
                         f"{str(s.get('local_windows',''))[:60]} | {str(s.get('utc_windows',''))[:60]} | "
                         f"{str(s.get('posts_per_day_per_account',''))[:20]} | {str(s.get('rationale',''))[:170]} |")
            L.append("")

        cp = r.get("channel_plan") or {}
        if cp:
            L.append("### План каналов")
            if cp.get("total_channels_recommended"):
                L.append(f"- **сколько каналов**: {cp['total_channels_recommended']}")
            if cp.get("split_logic"):
                L.append(f"- **логика деления**: {cp['split_logic']}")
            if cp.get("channel_slots"):
                L += ["", "| Слот | Тема | Ники | Формат | Игра |", "|---|---|---|---|---|"]
                for sl in cp["channel_slots"][:20]:
                    handles = ", ".join(str(x) for x in (sl.get("handle_examples") or [])[:3])
                    L.append(f"| {str(sl.get('slot',''))[:28]} | {str(sl.get('theme',''))[:90]} | "
                             f"{handles[:60]} | {str(sl.get('content_format',''))[:60]} | {str(sl.get('target_game',''))[:24]} |")
            L.append("")

        if r.get("content_angles"):
            L += ["### Идеи контента", "", "| Хук | Формат | Почему зайдёт здесь | CTA |", "|---|---|---|---|"]
            for a in r["content_angles"][:20]:
                L.append(f"| {str(a.get('hook','')).replace('|','/')[:130]} | {str(a.get('format',''))[:40]} | "
                         f"{str(a.get('why_local',''))[:150]} | {str(a.get('cta',''))[:60]} |")
            L.append("")

        for title, key in (("Воронка", "funnel"), ("Гео-техника", "proxy_and_account_geo"), ("KPI", "kpis")):
            block = r.get(key) or {}
            if block:
                L.append(f"### {title}")
                for k, v in block.items():
                    if v and not k.startswith("_"):
                        L.append(f"- **{k}**: {v if not isinstance(v, list) else ', '.join(map(str, v))}")
                L.append("")

        if r.get("competition"):
            L += ["### Конкуренция", "", str(r["competition"]), ""]
        if r.get("risks"):
            L += ["### Риски", ""] + [f"- {x}" for x in r["risks"]] + [""]
        if r.get("sources"):
            L += ["### Источники", ""] + [f"- {x}" for x in r["sources"][:25]] + [""]
    return "\n".join(L) + "\n"


def main() -> int:
    reports = load_reports()
    if not reports:
        print("нет отчётов в research/raw/geo__*.json")
        return 1
    geos = build_geos(reports)
    (ROOT / "data" / "geos.json").write_text(
        json.dumps(geos, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "docs" / "02-geo-playbooks.md").write_text(build_playbooks(reports), encoding="utf-8")
    print(f"собрано стран: {len(reports)}")
    for g in geos["geos"]:
        print(f"  {g['code']:10} p{g['priority']}{'!' if g.get('payment_blocked') else ' '} lang={g['content_language']:3} "
              f"tier={g['price_tier']:5} entry={g['entry_point']:9} "
              f"games={len(g['top_games']):2} slang={len(g['slang']):2} "
              f"local_ip={'да' if g['needs_local_ip'] else 'нет'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
