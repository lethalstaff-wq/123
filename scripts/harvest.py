#!/usr/bin/env python3
"""Забирает результаты агентов из журналов воркфлоу в research/raw/.

Имя файла включает идентификатор прогона для сводных агентов: у каждого воркфлоу
свой агент с меткой "audit", и без разведения они перетирали друг друга.

Читаются ТОЛЬКО прогоны ресерча из RUN_TAG. В той же директории живут журналы
любых других воркфлоу сессии — аудитов готовности, разовых проверок, — и без
этого фильтра их агенты сыпались в research/raw как исследовательские отчёты.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

WF = Path("/root/.claude/projects/-home-user-123/f5c4f68f-6b67-54eb-966c-5cf75718754c/"
          "subagents/workflows")
OUT = Path(__file__).resolve().parent.parent / "research" / "raw"

# какому прогону какой смысловой суффикс дать сводному агенту
RUN_TAG = {
    "wf_df28120e-009": "platform",
    "wf_6205bb48-21b": "product",
    "wf_7f7440d1-f8f": "geo_west",
    "wf_c6094453-979": "geo_mena_asia",
    "wf_992be095-60f": "geo_africa_cis_latam",
    "wf_3971f315-2a9": "geo_west",
}


def _safe(label: str) -> str:
    """Метка агента -> безопасное имя файла."""
    return re.sub(r"[^0-9A-Za-zА-Яа-я_.-]+", "_", label).strip("_")[:80] or "unnamed"


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    before = {p.name for p in OUT.glob("*.json")}
    saved: dict[str, str] = {}
    inflight: list[str] = []

    for journal in sorted(WF.glob("*/journal.jsonl")):
        run = journal.parent.name
        if run not in RUN_TAG:                       # чужой воркфлоу, не ресерч
            continue
        tag = RUN_TAG[run]
        labels, done = {}, set()
        for line in journal.read_text(encoding="utf-8").splitlines():
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("type") == "started":
                labels[ev["agentId"]] = ev.get("label", "?")
            elif ev.get("type") == "result" and ev.get("result"):
                done.add(ev["agentId"])
                label = str(labels.get(ev["agentId"], ev["agentId"]))
                # метки сводных агентов одинаковы у разных прогонов -> разводим по прогону
                if label.startswith("audit"):
                    name = f"audit__{tag}.json"
                else:
                    # метку пишет автор воркфлоу, и в ней может оказаться что
                    # угодно, включая слэш: без чистки имя файла превращается
                    # в несуществующий путь и весь заход падает на полпути
                    name = _safe(label.replace(":", "__")) + ".json"
                # Одну и ту же страну могли посчитать два агента из разных прогонов.
                # Перезаписывать нельзя: расхождение вердиктов — это сигнал о том,
                # насколько вывод устойчив, и он должен дойти до отчёта.
                target = OUT / name
                payload = json.dumps(ev["result"], ensure_ascii=False, indent=2)
                if target.exists() and target.read_text(encoding="utf-8") != payload:
                    alt = OUT / name.replace(".json", "__alt.json")
                    if not alt.exists() or alt.read_text(encoding="utf-8") != payload:
                        alt.write_text(payload, encoding="utf-8")
                        saved[alt.name] = label + " (второй расчёт)"
                else:
                    target.write_text(payload, encoding="utf-8")
                    saved[name] = label
        inflight += [f"{tag}:{v}" for k, v in labels.items() if k not in done]

    after = {p.name for p in OUT.glob("*.json")}
    geo = sorted(n.replace("geo__", "").replace(".json", "") for n in after if n.startswith("geo__"))
    topics = sorted(n.replace("r__", "").replace(".json", "") for n in after if n.startswith("r__"))
    audits = sorted(n for n in after if n.startswith("audit__"))

    print(f"отчётов в research/raw: {len(after)} (новых за этот заход: {len(after - before)})")
    print(f"  страны ({len(geo)}): {', '.join(geo)}")
    print(f"  темы ({len(topics)}): {', '.join(topics)}")
    print(f"  сводные аудиты ({len(audits)}): {', '.join(a.replace('audit__','').replace('.json','') for a in audits)}")
    if inflight:
        print(f"  ещё в работе ({len(set(inflight))}): {', '.join(sorted(set(inflight))[:12])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
