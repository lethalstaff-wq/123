#!/usr/bin/env python3
"""Собирает тематические документы из отчётов ресерча.

Каждый документ — это отчёт агента, приведённый к читаемому виду с сохранением
источников. Скрипт идемпотентен: запускается повторно по мере готовности агентов.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "research" / "raw"

# какой документ из каких отчётов собирается
DOCS = {
    "01-strategy.md": {
        "title": "Стратегия: что реально управляет гео-выдачей",
        "intro": ("Центральный вопрос проекта: можно ли выбрать страну зрителя. "
                  "Ответ ресерча — да, но только на уровне страны, и не тем способом, "
                  "которым это обычно пытаются делать."),
        "parts": ["r__geo_targeting_truth", "r__tiktok_mechanics", "r__shorts_mechanics",
                  "r__reels_mechanics"],
    },
    "04-content-system.md": {
        "title": "Контент: тактики, форматы, хуки",
        "intro": ("Разбор реальных гайдов по алгоритмам и трафику плюс форматы, которые "
                  "выдерживают массовое производство."),
        "parts": ["r__guides_ru_en", "r__guides_multiling", "r__content_bank_research",
                  "r__myths"],
    },
    "05-funnel-monetization.md": {
        "title": "Воронка, платежи и монетизация",
        "intro": ("Самый недооценённый блок: платёжный рельс определяет, возможен ли "
                  "бизнес вообще, и ограничивает даже стиль маркетинга."),
        "parts": ["r__payments_stack", "r__saas_pricing", "r__discord_funnel",
                  "r__delivery_licensing", "r__funnel_conversion"],
    },
    "03-channel-network.md": {
        "title": "Сеть каналов, прокси и автоматизация",
        "intro": ("Как разложить каналы, что реально даёт инфраструктура и где граница "
                  "между масштабированием и потерей аккаунтов."),
        "parts": ["r__network_architecture", "r__proxy_infra", "r__automation_apis",
                  "r__bought_accounts", "r__alt_platforms", "r__tooling_automation"],
    },
    "07-product.md": {
        "title": "Продукт: ассортимент, доставка, серые зоны",
        "intro": "Что продавать, как выдавать автоматически и чего не делать.",
        "parts": ["r__hardware_side", "r__accounts_grey", "r__cases_saas_traffic",
                  "r__where_clients_are", "r__delivery_models", "r__legal_policy_product"],
    },
}


def render_report(name: str, r: dict) -> list[str]:
    L = [f"## {name.replace('r__', '').replace('_', ' ')}", ""]
    if r.get("summary"):
        L += ["### Вывод", "", r["summary"], ""]
    if r.get("key_numbers"):
        L += ["### Цифры", ""] + [f"- {x}" for x in r["key_numbers"]] + [""]
    if r.get("machine_spec_notes"):
        L += ["### Правила и константы для системы", ""] + \
             [f"- {x}" for x in r["machine_spec_notes"]] + [""]
    if r.get("findings"):
        L += ["### Находки", "",
              "| Утверждение | Тип | Доверие | Источник | Что делать |", "|---|---|---|---|---|"]
        for f in r["findings"]:
            L.append(
                f"| {str(f.get('claim','')).replace('|','/')} | {f.get('kind','')} | "
                f"{f.get('confidence','')} | {str(f.get('source','')).replace('|','/')[:170]} | "
                f"{str(f.get('actionable','')).replace('|','/')[:320]} |")
        L.append("")
    if r.get("risks"):
        L += ["### Риски", ""] + [f"- {x}" for x in r["risks"]] + [""]
    if r.get("open_questions"):
        L += ["### Открытые вопросы", ""] + [f"- {x}" for x in r["open_questions"]] + [""]
    return L


def main() -> int:
    built = []
    for fname, cfg in DOCS.items():
        parts = []
        missing = []
        for part in cfg["parts"]:
            p = RAW / f"{part}.json"
            if not p.exists():
                missing.append(part)
                continue
            try:
                parts.append((part, json.loads(p.read_text(encoding="utf-8"))))
            except json.JSONDecodeError:
                missing.append(f"{part} (битый JSON)")
        if not parts:
            continue
        L = [f"# {cfg['title']}", "", cfg["intro"], "",
             f"Собрано из отчётов: {', '.join(p for p, _ in parts)}.", ""]
        if missing:
            L += [f"> Ещё не готово: {', '.join(missing)} — документ будет дополнен.", ""]
        for part, r in parts:
            L += ["---", ""] + render_report(part, r)
        path = ROOT / "docs" / fname
        path.write_text("\n".join(L) + "\n", encoding="utf-8")
        built.append((fname, path.stat().st_size, len(parts), len(missing)))

    for f, size, got, miss in built:
        print(f"  docs/{f:28} {size:>8} байт  (готово частей: {got}, ждём: {miss})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
