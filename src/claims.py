"""Валидатор обещаний: барьер между генератором контента и публикацией.

Зачем это код, а не пункт в инструкции: аудитория этой нишы технически грамотна.
Числа без контекста железа («+60 FPS», «x2 FPS», «снизим пинг») разбираются в
комментариях, и это стоит дороже, чем весь выигрыш от громкого хука: возвраты,
жалобы в платёжку и мёртвый канал. Правила и потолки лежат в data/offers.json,
здесь только их применение.

Проверяются хук, подпись, заголовок и текст на экране — до рендера и до публикации.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import offers

# Модели железа: каждый альтернативный вариант со своими границами слова.
# Наивный вариант вида r"\b(...|rx\s?\d|...)\b" не матчит "RX 6600" — граница
# слова после первой цифры не срабатывает, и валидатор блокировал корректные хуки.
HARDWARE_HINT = re.compile(
    r"(?i)(?:"
    r"\b(?:gtx|rtx|radeon|geforce|ryzen|intel|iris\s?xe|apu|igpu)\b"
    r"|\brx\s?\d{3,4}\b"
    r"|\bcore\s?i[3579]\b"
    r"|\bi[3579][\s-]?\d{4,5}[a-z]{0,2}\b"
    r"|\bi[3579]\b"
    r"|\bmx\s?\d{3}\b"
    r"|\bultra\s?[579]\b"
    r"|\b\d{4}[a-z]{0,2}x3d\b"
    r"|встро\w+\s+график"
    r")"
)
GAME_HINT_FIELDS = ("game",)
FPS_NUMBER = re.compile(r"(?i)(\d{2,3})\s*(?:fps|фпс)")
LATENCY_MS = re.compile(r"(?i)[-−]\s*(\d{1,3})\s*ms")
PERCENT = re.compile(r"(?i)\+\s*(\d{1,3})\s*%")


@dataclass
class ClaimVerdict:
    ok: bool
    violations: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.ok


def _rules() -> dict:
    return offers().get("claim_rules", {})


def _caps() -> dict:
    return _rules().get("numeric_caps", {})


def check_text(text: str, *, game: str | None = None) -> ClaimVerdict:
    """Проверяет одну строку (хук, подпись, заголовок, текст на экране)."""
    if not text:
        return ClaimVerdict(True)
    problems: list[str] = []

    for pattern in _rules().get("blocklist_regex", []):
        try:
            if re.search(pattern, text):
                problems.append(f"запрещённая формулировка: /{pattern[:60]}/")
        except re.error:
            continue

    caps = _caps()
    if not caps.get("ping_reduction_claims_allowed", False):
        if re.search(r"(?i)\bping\b|\bпинг", text):
            problems.append("обещание по пингу: пинг определяется маршрутом, твиками не меняется")

    # числа FPS допустимы только рядом с указанием железа — иначе это непроверяемое обещание
    fps_nums = [int(m) for m in FPS_NUMBER.findall(text)]
    if fps_nums and not HARDWARE_HINT.search(text):
        problems.append("число FPS без указания железа (нужен GPU/CPU в том же тексте)")

    # прирост в процентах не выше потолков
    for pct in (int(m) for m in PERCENT.findall(text)):
        if pct > int(caps.get("max_claimed_1pct_low_gain_pct", 50)):
            problems.append(f"заявленный прирост {pct}% выше потолка "
                            f"{caps.get('max_claimed_1pct_low_gain_pct')}%")

    for ms in (int(m) for m in LATENCY_MS.findall(text)):
        if ms > int(caps.get("max_claimed_latency_reduction_ms", 20)):
            problems.append(f"заявленное снижение латентности {ms} ms выше потолка "
                            f"{caps.get('max_claimed_latency_reduction_ms')} ms")

    # пара «было → стало» проверяется на реалистичность прироста среднего FPS
    if len(fps_nums) >= 2:
        lo, hi = min(fps_nums), max(fps_nums)
        if lo > 0:
            gain = (hi - lo) / lo * 100
            ceiling = int(caps.get("max_claimed_1pct_low_gain_pct", 50))
            if gain > ceiling:
                problems.append(f"прирост {lo}→{hi} fps = +{gain:.0f}% выше потолка {ceiling}%")

    return ClaimVerdict(not problems, problems)


def check_plan(hook: str, caption: str, title: str, beats: list[str] | None = None,
               game: str | None = None) -> ClaimVerdict:
    """Проверяет весь текстовый набор одного видео."""
    problems: list[str] = []
    for label, text in (("хук", hook), ("подпись", caption), ("заголовок", title)):
        v = check_text(text, game=game)
        problems += [f"{label}: {p}" for p in v.violations]
    for i, beat in enumerate(beats or []):
        v = check_text(beat, game=game)
        problems += [f"бит {i + 1}: {p}" for p in v.violations]
    return ClaimVerdict(not problems, problems)


def disclaimer() -> str:
    return offers().get("product", {}).get("required_disclaimer", "")


def never_does() -> list[str]:
    return offers().get("product", {}).get("what_it_never_does", [])
