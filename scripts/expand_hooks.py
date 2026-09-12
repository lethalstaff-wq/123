#!/usr/bin/env python3
"""Разворачивает шаблоны хуков в конкретные строки: шаблон x игра x число x GPU x сленг.

Зачем: авто-заливу нужны ТЫСЯЧИ разных первых фраз. Ручной банк на 200 строк
превращается в дубли уже на второй неделе, а повторяющийся хук на 20 каналах —
самый заметный признак сетки.

Запуск:
    python scripts/expand_hooks.py --per-template 40 --out data/hooks_expanded.json
"""
from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BANK = ROOT / "data" / "content_bank.json"
GEOS = ROOT / "data" / "geos.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-template", type=int, default=40,
                    help="сколько конкретных хуков сделать из одного шаблона")
    ap.add_argument("--out", default=str(ROOT / "data" / "hooks_expanded.json"))
    ap.add_argument("--seed", type=int, default=1337)
    args = ap.parse_args()

    bank = json.loads(BANK.read_text(encoding="utf-8"))
    geos = {g["code"]: g for g in json.loads(GEOS.read_text(encoding="utf-8"))["geos"]}
    rng = random.Random(args.seed)

    # Размножаем ПО ГЕО, а не по языку: игры и сленг у us и uk разные, хотя язык один.
    # Иначе британское "peak" уезжает в американские хуки и контент перестаёт читаться
    # как местный — а это главный рычаг гео-таргетинга.
    games_all = bank["games"]
    gpus = bank["gpus"]
    fps = bank["fps_claims"]

    out: list[dict] = []
    seen: set[str] = set()
    for geo in geos.values():
        lang = geo["content_language"]
        templates = [t for t in bank["hooks"] if t["lang"] == lang]
        if not templates:
            continue
        games = geo.get("top_games") or games_all
        slang = geo.get("slang") or [""]
        for tmpl in templates:
            made = 0
            attempts = 0
            while made < args.per_template and attempts < args.per_template * 12:
                attempts += 1
                # Пара чисел должна быть правдоподобной для аудитории со слабым ПК:
                # старт низкий, прирост умеренный. "с 144 до 174" читается как вранье
                # и бьёт по доверию сильнее, чем помогает CTR.
                lo = rng.choice([f for f in fps if f <= 75])
                # прирост ограничен потолком шаблона: 15% для среднего FPS,
                # до 50% для 1% low. Иначе получаются обещания вида "24 -> 60 fps"
                # (+150%), которые валидатор справедливо блокирует
                cap = int(tmpl.get("gain_cap_pct", 15))
                hi_max = int(lo * (1 + cap / 100))
                candidates = [f for f in fps if lo < f <= hi_max]
                hi = rng.choice(candidates) if candidates else lo + max(2, int(lo * cap / 100))
                game = rng.choice(games)
                text = (tmpl["text"]
                        .replace("{game}", game)
                        .replace("{fps2}", str(hi))
                        .replace("{fps}", str(lo))
                        .replace("{gpu}", rng.choice(gpus))
                        .replace("{slang}", rng.choice(slang)))
                key = f"{geo['code']}|{text}"
                if key in seen:
                    continue
                seen.add(key)
                out.append({
                    "geo": geo["code"],
                    "lang": lang,
                    "text": text.strip(),
                    "from_template": tmpl["text"],
                    "formats": tmpl.get("formats", []),
                    "games": [game] if "{game}" in tmpl["text"] else [],
                })
                made += 1

    Path(args.out).write_text(
        json.dumps({"_meta": {"generated_from": "content_bank.json",
                              "note": "Файл машинный: не редактировать руками, менять шаблоны в content_bank.json"},
                    "count": len(out), "hooks": out}, ensure_ascii=False, indent=2),
        encoding="utf-8")
    by_geo: dict[str, int] = {}
    for h in out:
        by_geo[h["geo"]] = by_geo.get(h["geo"], 0) + 1
    print(f"сгенерировано хуков: {len(out)}")
    for k, v in sorted(by_geo.items(), key=lambda kv: -kv[1]):
        print(f"  {k}: {v}")
    print(f"-> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
