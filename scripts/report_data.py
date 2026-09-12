#!/usr/bin/env python3
"""Извлечение данных для отчёта из data/*.json и research/raw/*.json.

Отдельный модуль, потому что отчёт должен пересобираться по мере готовности
ресерча: генератор разметки не знает, откуда берутся числа, а этот модуль не
знает, как они будут выглядеть.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RAW = ROOT / "research" / "raw"

NAMES_RU = {
    "us": "США", "ca": "Канада", "uk": "Великобритания", "de": "Германия и DACH",
    "fr": "Франция", "es": "Испания", "it": "Италия", "pl": "Польша",
    "nl_be": "Нидерланды и Бельгия", "nordics": "Скандинавия", "cee": "Восточная Европа",
    "tr": "Турция", "au_nz": "Австралия и НЗ", "pt_gr": "Португалия и Греция",
    "sa": "Саудовская Аравия", "ae": "ОАЭ", "eg": "Египет", "iq": "Ирак",
    "maghreb": "Магриб", "gulf_small": "Малый Залив", "id": "Индонезия",
    "ph": "Филиппины", "vn": "Вьетнам", "th_my": "Таиланд и Малайзия", "in": "Индия",
    "jp": "Япония", "kr": "Южная Корея", "ng": "Нигерия", "ke_tz": "Восточная Африка",
    "za": "ЮАР", "af_fr": "Франкофонная Африка", "ru": "Россия",
    "kz_uz": "Казахстан и Узбекистан", "ua_by": "Украина и Беларусь",
    "br": "Бразилия", "mx": "Мексика и LatAm",
}

CONF_LABEL = {
    "high": ("подтверждено", "ok"),
    "medium": ("вероятно", "warn"),
    "low": ("не подтверждено", "mute"),
}
KIND_LABEL = {
    "official_policy": "политика площадки",
    "platform_docs": "документация",
    "industry_data": "индустриальные данные",
    "practitioner_report": "опыт практиков",
    "myth_debunk": "разбор мифа",
    "inference": "вывод",
}


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def d(name: str) -> dict:
    return load(DATA / name)


def r(name: str) -> dict:
    return load(RAW / f"{name}.json")


def reports() -> dict[str, dict]:
    return {p.stem: load(p) for p in sorted(RAW.glob("*.json"))}


def stats() -> dict:
    reps = reports()
    geo = [k for k in reps if k.startswith("geo__")]
    topics = [k for k in reps if k.startswith("r__")]
    # часть отчётов (сводные агенты) возвращает не структуру, а текст —
    # такие пропускаем, иначе статистика падает на первом же из них
    def dict_findings(v: dict) -> list[dict]:
        items = v.get("findings") if isinstance(v, dict) else None
        return [f for f in (items or []) if isinstance(f, dict)]

    findings = sum(len(dict_findings(v)) for v in reps.values())
    sources = set()
    for v in reps.values():
        if not isinstance(v, dict):
            continue
        for f in dict_findings(v):
            src = str(f.get("source") or "").strip()
            if src:
                sources.add(src[:120])
        for s in v.get("sources") or []:
            if isinstance(s, str) and s.strip():
                sources.add(s[:120])
    return {
        "countries": len(geo),
        "topics": len(topics),
        "reports": len(reps),
        "findings": findings,
        "sources": len(sources),
    }


def findings(topic: str, limit: int = 8, min_conf: tuple[str, ...] = ("high", "medium")) -> list[dict]:
    """Находки по теме, отсортированные по уровню доверия."""
    order = {"high": 0, "medium": 1, "low": 2}
    raw = r(topic).get("findings") or []
    items = [f for f in raw if isinstance(f, dict) and f.get("confidence") in min_conf]
    items.sort(key=lambda f: order.get(f.get("confidence", "low"), 3))
    return items[:limit]


def geos() -> list[dict]:
    return d("geos.json").get("geos", [])


def _money(text: str) -> float | None:
    m = re.search(r"\$\s?(\d{1,2}(?:[.,]\d{1,2})?)", str(text))
    if m:
        return float(m.group(1).replace(",", "."))
    m = re.search(r"(\d{1,2}(?:[.,]\d{1,2})?)\s*USD", str(text))
    return float(m.group(1).replace(",", ".")) if m else None


def geo_rows() -> list[dict]:
    """Строки гео-матрицы: только то, что можно показать без домыслов."""
    rows = []
    for g in geos():
        pts = g.get("price_points_usd") or []
        price = (sum(pts) / len(pts)) if pts else None
        report = r(f"geo__{g['code']}")
        games = g.get("top_games") or []
        rows.append({
            "code": g["code"],
            "name": NAMES_RU.get(g["code"],
                        (g.get("name") or g["code"]).split("(")[0].split("—")[0].strip()[:30]),
            "priority": g.get("priority", 9),
            "lang": g.get("content_language", "?"),
            "games": games[:3],
            "price": price,
            "price_lo": min(pts) if pts else None,
            "price_hi": max(pts) if pts else None,
            "tier": g.get("price_tier", "?"),
            "entry": g.get("entry_point", "?"),
            "blocked": bool(g.get("payment_blocked")),
            "needs_split": bool(g.get("needs_split")),
            "slang": (g.get("slang") or [])[:6],
            "verdict": (report.get("verdict_reason") or g.get("verdict_reason") or "")[:260],
            "payments": (g.get("payment_methods") or [])[:4],
        })
    rows.sort(key=lambda x: (x["priority"], -(x["price"] or 0)))
    return rows


def decision_order() -> list[dict]:
    """Порядок решений. Это реальная последовательность: шаги необратимы."""
    pay = d("payments.json")
    return [
        {
            "step": "Юрлицо и платёжный рельс",
            "why": "Страна юрлица фиксируется навсегда при первом живом платеже, и Stripe не работает ни в одной стране СНГ. Это единственный необратимый шаг во всём проекте.",
            "action": "Иностранное юрлицо со Stripe (так сделал EXM Tweaks — s.r.o. в Словакии) либо Lemon Squeezy с выплатами на банк, если оператор в Армении, Азербайджане, Казахстане, Молдове или Узбекистане. Paddle исключить: его правила дословно запрещают софт для улучшения производительности устройства.",
            "cost": "Stripe Atlas — $500 разово, далее $100 в год. Lemon Squeezy — около 7% + $0.50 с платежа.",
        },
        {
            "step": "Границы продукта",
            "why": "Античиты не банят за твики, но требуют Secure Boot, TPM и IOMMU — ровно то, что твикеры отключают. Продукт, выключивший их, лишает клиента возможности запустить игру.",
            "action": "Зафиксировать список того, что продукт не делает никогда, и пре-флайт проверку перед применением. Никакого драйвера уровня ядра: класс «оптимизаторов с драйвером» уже в публичном denylist EA.",
            "cost": "Ноль денег, но определяет, будут ли возвраты.",
        },
        {
            "step": "Два стартовых гео",
            "why": "Гранулярность органической гео-выдачи — страна. Ни город, ни штат не влияют. Значит выбор гео — это выбор языка контента и платёжеспособности, а не прокси.",
            "action": "Одно платёжеспособное гео на английском плюс одно объёмное для теста креативов. Заблокированные для платежей страны в таргет не берутся.",
            "cost": "Страново-корректные IP, без city-таргета.",
        },
        {
            "step": "Сетка каналов и контент",
            "why": "Монетизация сети невозможна: с 01.02.2027 выплаты Shorts требуют 10 млн просмотров за 90 дней на канал. Каналы — расходник, работающий на клики в bio.",
            "action": "Деление по игре, затом по формату, затем по железу. Язык — только при смене гео. Хук на языке гео с локальным сленгом и указанием железа.",
            "cost": "Основное время оператора.",
        },
        {
            "step": "Измерение и отсечение",
            "why": "Время постинга — фактор третьего порядка, а данные источников противоречивы. Значит расписание проверяется на своей сетке, а не берётся из чужой таблицы.",
            "action": "Половина каналов в прайм, половина в окна низкой конкуренции, арм фиксируется на 21 день, сравнение по медиане. Гео считается рабочим по доле просмотров из целевой страны, а не по общему числу просмотров.",
            "cost": "21 день и минимум 400 постов на плечо.",
        },
    ]


def geo_factors() -> list[dict]:
    """Факторы гео-выдачи по силе влияния — ядро ответа на исходный вопрос."""
    return [
        {"rank": "S", "factor": "Страна аккаунта, выведенная из SIM и/или IP",
         "note": "Аудит с выделенным прокси на аккаунт: «different locations have a strong impact on the posts shown by TikTok», и локация влияет сильнее языка профиля.",
         "source": "Boeker & Urman, arXiv:2201.12271", "conf": "high"},
        {"rank": "S", "factor": "Поведение первых зрителей (досмотр, реплей, шер)",
         "note": "TikTok официально: досмотр длинного видео до конца получает больший вес, чем совпадение страны зрителя и автора. Досмотр перебивает гео.",
         "source": "TikTok Newsroom, How TikTok recommends videos", "conf": "high"},
        {"rank": "S", "factor": "Граф подписок",
         "note": "Подписка — сильнейший фактор персонализации в аудите. Подписчики из целевой страны — единственный долгоиграющий гео-якорь.",
         "source": "Boeker & Urman, arXiv:2201.12271", "conf": "high"},
        {"rank": "A", "factor": "Язык озвучки и текста на экране",
         "note": "Работает не как метаданные, а через досмотр: чужой язык физически убивает удержание у нецелевой аудитории. Самый дешёвый рычаг.",
         "source": "механика через фактор досмотра", "conf": "high"},
        {"rank": "A", "factor": "Платный таргет",
         "note": "Единственный инструмент с точным гео-контролем: страна, штат, округ, DMA, город, индекс — до 3000 локаций на группу объявлений.",
         "source": "TikTok Ads Location Targeting", "conf": "high"},
        {"rank": "A", "factor": "Язык метаданных",
         "note": "Подписи, звук и хештеги — второй по силе блок сигналов у TikTok. У YouTube это записываемые поля defaultLanguage и defaultAudioLanguage.",
         "source": "TikTok Newsroom; YouTube Data API", "conf": "high"},
        {"rank": "B", "factor": "Языковая настройка устройства и страна профиля",
         "note": "Официально названы сигналами с «lower weight» относительно остальных.",
         "source": "TikTok Newsroom", "conf": "high"},
        {"rank": "—", "factor": "Город внутри страны",
         "note": "Влияния нет. Эксперимент с GPS-спуфингом в Манхэттен, Collin County и Cobb County дал одинаковую структуру выдачи. Подстрановая гранулярность есть только в платных кабинетах.",
         "source": "arXiv:2501.17831", "conf": "medium"},
    ]


def slots() -> list[dict]:
    sch = d("schedule.json")
    arms = sch.get("experiment_arms", {})
    a = set(arms.get("arm_A_prime") or [])
    out = []
    for sid, meta in (sch.get("slots_local") or {}).items():
        hh, mm = (int(x) for x in str(meta.get("time", "00:00")).split(":"))
        out.append({
            "id": sid, "time": meta.get("time", ""), "minutes": hh * 60 + mm,
            "label": meta.get("label", ""), "arm": "A" if sid in a else "B",
        })
    out.sort(key=lambda s: s["minutes"])
    return out
