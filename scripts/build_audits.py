#!/usr/bin/env python3
"""Сводные аудиты: research/raw/audit__*.json -> docs/08-audit-*.md + data/audit_stats.json.

Аудиторы возвращают разное: кто-то markdown, кто-то JSON-объект. Руками это
сводить нельзя — счётчик подтверждений уезжает от текста, и отчёт начинает
обещать проверок больше, чем их было. Поэтому и документ, и статистика
собираются из одного входа одним проходом.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "research" / "raw"
DOCS = ROOT / "docs"
DATA = ROOT / "data"

TITLES = {
    "platform": "Аудит: механика площадок и единый свод правил",
    "product": "Аудит: продукт, твики и обещания",
    "geo_west": "Аудит: западный блок (US/UK/CA/EU/ANZ/TR)",
    "geo_mena_asia": "Аудит: Ближний Восток и Азия",
    "geo_africa_cis_latam": "Аудит: Африка, СНГ и Латинская Америка",
}

HEADS = ("ПОДТВЕРЖДЕНО", "ОПРОВЕРГНУТО", "УСТАРЕЛО", "ЧАСТИЧНО ЛОЖНО", "ЛОЖНО", "ПРОБЕЛ")
# Вердикт живёт либо в жирной ячейке таблицы, либо в поле JSON. Хвост важен:
# "ПОДТВЕРЖДЕНО ЧАСТИЧНО" — не то же самое, что "ПОДТВЕРЖДЕНО".
VERDICT = re.compile(r"\*\*(" + "|".join(HEADS) + r")([^*]*)\*\*"
                     r"|\"verdict\"\s*:\s*\"(" + "|".join(HEADS) + r")([^\"]*)\"")


def classify(text: str) -> dict[str, int]:
    out = {"confirmed": 0, "partial": 0, "corrected": 0, "refuted": 0, "gap": 0}
    for bold, bold_tail, field, field_tail in VERDICT.findall(text):
        head, tail = (bold, bold_tail) if bold else (field, field_tail)
        tail = tail.upper()
        if head == "ПОДТВЕРЖДЕНО":
            out["partial" if "ЧАСТИЧНО" in tail else "confirmed"] += 1
        elif head == "УСТАРЕЛО":
            out["corrected"] += 1
        elif head == "ПРОБЕЛ":
            out["gap"] += 1
        else:
            out["refuted"] += 1
    return out


def _cell(v) -> str:
    if isinstance(v, (list, tuple)):
        return "; ".join(_cell(x) for x in v)
    if isinstance(v, dict):
        return "; ".join(f"{k}: {_cell(x)}" for k, x in v.items())
    return str(v).replace("|", "\\|").replace("\n", " ")


def _table(rows: list[dict]) -> str:
    cols: list[str] = []
    for row in rows:
        cols += [k for k in row if k not in cols]
    head = "| " + " | ".join(cols) + " |\n| " + " | ".join("---" for _ in cols) + " |\n"
    body = "".join("| " + " | ".join(_cell(r.get(c, "")) for c in cols) + " |\n" for r in rows)
    return head + body


def render(node, level: int = 2) -> str:
    """JSON-ответ аудитора -> читаемый markdown. Списки однородных словарей
    становятся таблицами: именно в них лежат вердикты."""
    if isinstance(node, dict):
        out = []
        for key, val in node.items():
            title = key.replace("_", " ").capitalize()
            if isinstance(val, (dict, list)):
                out.append(f"\n{'#' * min(level, 6)} {title}\n")
                out.append(render(val, level + 1))
            else:
                out.append(f"- **{title}:** {val}\n")
        return "".join(out)
    if isinstance(node, list):
        if node and all(isinstance(x, dict) for x in node):
            return _table(node) + "\n"
        return "".join(f"- {_cell(x)}\n" for x in node) + "\n"
    return f"{node}\n"


def to_markdown(body: str) -> str:
    """Снимает служебную преамбулу агента и разворачивает JSON-ответы."""
    try:
        return render(json.loads(body)).strip()
    except json.JSONDecodeError:
        pass
    cut = body.find("\n# ")
    if cut > 0 and cut < 400:
        body = body[cut + 1:]
    return body.strip().lstrip("-").strip()


def main() -> int:
    stats: dict[str, dict] = {}
    for path in sorted(RAW.glob("audit__*.json")):
        tag = path.stem.replace("audit__", "")
        body = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(body, str):
            body = json.dumps(body, ensure_ascii=False, indent=2)
        title = TITLES.get(tag, f"Аудит: {tag}")
        doc = (f"# {title}\n\nНезависимая проверка утверждений исследователей "
               f"по первоисточникам.\n\n{to_markdown(body)}\n")
        (DOCS / f"08-audit-{tag}.md").write_text(doc, encoding="utf-8")
        stats[tag] = {**classify(body), "size": len(body)}

    total = {k: sum(v[k] for v in stats.values())
             for k in ("confirmed", "partial", "corrected", "refuted", "gap")}
    stats["_total"] = total
    (DATA / "audit_stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"аудитов: {len(stats) - 1}; " + ", ".join(f"{k}={v}" for k, v in total.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
