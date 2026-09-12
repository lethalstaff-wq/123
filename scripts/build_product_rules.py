#!/usr/bin/env python3
"""Собирает data/product_rules.json и docs/06-risks-compliance.md из отчётов ресерча.

Почему отдельный файл правил продукта: главный риск проекта — не баны за твики
(ни один мейджорный античит за них не банит), а то, что продукт ЛОМАЕТ ЗАПУСК
игр. В 2025-2026 античиты требуют Secure Boot, TPM 2.0, IOMMU и HVCI — то есть
именно те механизмы, которые классические 'FPS-твикеры' отключают. Клиент,
которому продукт выключил Secure Boot, не сможет запустить Valorant, Black Ops 7,
Battlefield 6 и турниры Fortnite — это возвраты, чарджбеки и потеря платёжки.

Полные формулировки берутся из отчётов без сокращений: это тот текст, который
попадёт в дисклеймер, правила Discord и чекбокс при оплате.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "research" / "raw"


def load(name: str) -> dict:
    p = RAW / f"{name}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def main() -> int:
    ac = load("r__anticheat_safety")
    eff = load("r__tweaks_efficacy")
    comp = load("r__exmtweaks_teardown")
    price = load("r__saas_pricing")

    if not ac:
        print("нет r__anticheat_safety.json — запусти после завершения продуктового прогона")
        return 1

    rules = {
        "_meta": {
            "purpose": "Машинные правила продукта: что он НИКОГДА не делает, что проверяет до применения и что обещает.",
            "source": "агенты anticheat_safety / tweaks_efficacy / exmtweaks_teardown / saas_pricing",
            "why_critical": ("Ни один мейджорный античит (EAC, Vanguard, VAC, BattlEye, RICOCHET, EA Javelin) "
                             "не банит за твики Windows, реестр, службы, конфиги и оверлеи. Реальный риск — "
                             "блокировка ЗАПУСКА игры: античиты требуют Secure Boot, TPM 2.0, IOMMU, HVCI, а "
                             "классические твикеры их отключают."),
        },
        "anticheat": {
            "summary": ac.get("summary", ""),
            "machine_rules": ac.get("machine_spec_notes", []),
            "risks": ac.get("risks", []),
            "findings": [
                {k: f.get(k) for k in ("claim", "evidence", "source", "source_date", "confidence", "actionable")}
                for f in ac.get("findings", [])
            ],
        },
        "efficacy": {
            "_purpose": "Что из твиков реально даёт прирост, а что снейк-ойл. Основа честных обещаний в контенте.",
            "summary": eff.get("summary", ""),
            "measured": eff.get("key_numbers", []),
            "machine_rules": eff.get("machine_spec_notes", []),
            "findings": [
                {k: f.get(k) for k in ("claim", "evidence", "source", "confidence", "actionable")}
                for f in eff.get("findings", [])
            ],
        },
        "competitors": {
            "summary": comp.get("summary", ""),
            "key_numbers": comp.get("key_numbers", []),
            "findings": [
                {k: f.get(k) for k in ("claim", "evidence", "source", "confidence", "actionable")}
                for f in comp.get("findings", [])
            ],
        },
        "pricing": {
            "summary": price.get("summary", ""),
            "key_numbers": price.get("key_numbers", []),
            "machine_rules": price.get("machine_spec_notes", []),
        },
    }
    (ROOT / "data" / "product_rules.json").write_text(
        json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

    L = ["# Риски, комплаенс и границы продукта", "",
         "Источник: агенты ресерча `anticheat_safety`, `tweaks_efficacy`, `exmtweaks_teardown`, `saas_pricing`.",
         "Машинная версия: `data/product_rules.json`.", "",
         "## Главный вывод", "", ac.get("summary", ""), "",
         "## Правила, которые продукт обязан соблюдать", ""]
    for r in ac.get("machine_spec_notes", []):
        L.append(f"- {r}")
    L += ["", "## Карта рисков", ""]
    for r in ac.get("risks", []):
        L.append(f"- {r}")

    L += ["", "## Доказательная база по античитам", "",
          "| Утверждение | Доверие | Источник | Что делать |", "|---|---|---|---|"]
    for f in ac.get("findings", []):
        L.append(f"| {str(f.get('claim','')).replace('|','/')} | {f.get('confidence','')} | "
                 f"{str(f.get('source','')).replace('|','/')[:160]} | "
                 f"{str(f.get('actionable','')).replace('|','/')[:300]} |")

    if eff:
        L += ["", "## Что из твиков реально работает", "", eff.get("summary", ""), "",
              "### Измеренные значения", ""]
        for n in eff.get("key_numbers", []):
            L.append(f"- {n}")
        L += ["", "### Правила для контента и оффера", ""]
        for n in eff.get("machine_spec_notes", []):
            L.append(f"- {n}")

    if comp:
        L += ["", "## Конкуренты", "", comp.get("summary", ""), "", "### Цифры рынка", ""]
        for n in comp.get("key_numbers", []):
            L.append(f"- {n}")

    if price:
        L += ["", "## Цены и упаковка", "", price.get("summary", ""), "", "### Опорные числа", ""]
        for n in price.get("key_numbers", []):
            L.append(f"- {n}")

    (ROOT / "docs" / "06-risks-compliance.md").write_text("\n".join(L) + "\n", encoding="utf-8")

    print(f"data/product_rules.json: {(ROOT / 'data' / 'product_rules.json').stat().st_size} байт")
    print(f"docs/06-risks-compliance.md: {(ROOT / 'docs' / '06-risks-compliance.md').stat().st_size} байт")
    print(f"правил античитов: {len(ac.get('machine_spec_notes', []))}, рисков: {len(ac.get('risks', []))}, "
          f"находок: {len(ac.get('findings', []))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
