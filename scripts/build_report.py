#!/usr/bin/env python3
"""Сборка отчёта в одну HTML-страницу из data/*.json и research/raw/*.json.

Запуск: python scripts/build_report.py  ->  report/index.html
Пересобирается по мере готовности ресерча, ничего не правится руками.
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import report_data as R  # noqa: E402

OUT = ROOT / "report" / "index.html"


def e(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def chip(conf: str) -> str:
    label, kind = R.CONF_LABEL.get(conf, ("нет данных", "mute"))
    return f'<span class="chip chip--{kind}">{e(label)}</span>'


# ─────────────────────────── графики ───────────────────────────

def chart_prices(rows: list[dict]) -> str:
    """Месячная цена подписки по гео. Одна серия — легенда не нужна, заголовок называет её."""
    data = [x for x in rows if x.get("price")]
    data.sort(key=lambda x: -x["price"])
    if not data:
        return ""
    top = max(x["price"] for x in data)
    row_h, gap, label_w, right_pad = 30, 8, 186, 200
    plot_w = 360
    h = len(data) * (row_h + gap) - gap
    w = label_w + plot_w + right_pad
    bars = []
    for i, x in enumerate(data):
        y = i * (row_h + gap)
        bw = max(3.0, x["price"] / top * plot_w)
        fill = "url(#hatch)" if x["blocked"] else "var(--c1)"
        bars.append(
            f'<text class="c-lab" x="{label_w - 10}" y="{y + row_h / 2 + 4}" text-anchor="end">{e(x["name"])}</text>'
            f'<rect x="{label_w}" y="{y + 4}" width="{bw:.1f}" height="{row_h - 8}" rx="4" fill="{fill}"/>'
            f'<text class="c-val" x="{label_w + bw + 8}" y="{y + row_h / 2 + 4}">'
            f'${x["price"]:.2f}{" · платёж заблокирован" if x["blocked"] else ""}</text>'
        )
    ticks = []
    for t in (0, top / 2, top):
        tx = label_w + t / top * plot_w
        ticks.append(f'<line class="c-grid" x1="{tx:.1f}" y1="-6" x2="{tx:.1f}" y2="{h}"/>'
                     f'<text class="c-tick" x="{tx:.1f}" y="{h + 16}" text-anchor="middle">${t:.0f}</text>')
    return (
        f'<figure class="figure"><div class="figure__scroll">'
        f'<svg viewBox="0 -12 {w} {h + 30}" width="{w}" height="{h + 42}" role="img" '
        f'aria-label="Рекомендованная месячная цена подписки по гео">'
        f'<defs><pattern id="hatch" width="7" height="7" patternTransform="rotate(45)" '
        f'patternUnits="userSpaceOnUse"><rect width="7" height="7" fill="var(--c2)" opacity="0.25"/>'
        f'<line x1="0" y1="0" x2="0" y2="7" stroke="var(--c2)" stroke-width="3"/></pattern></defs>'
        f'{"".join(ticks)}{"".join(bars)}</svg></div>'
        f'<figcaption>Рекомендованная цена месячной подписки, USD. Штриховка — страны, '
        f'которым платёжные системы не дают платить.</figcaption></figure>'
    )


def chart_slots(slots: list[dict]) -> str:
    """Шесть слотов постинга на 24-часовой шкале, разнесённые по плечам эксперимента."""
    if not slots:
        return ""
    w, h, pad_l, pad_r = 640, 150, 40, 40
    plot = w - pad_l - pad_r
    axis_y = 92
    marks, labels = [], []
    for i, s in enumerate(slots):
        x = pad_l + s["minutes"] / 1440 * plot
        color = "var(--c1)" if s["arm"] == "A" else "var(--c2)"
        up = i % 2 == 0
        ly = axis_y - 22 if up else axis_y + 30
        marks.append(
            f'<line x1="{x:.1f}" y1="{axis_y}" x2="{x:.1f}" y2="{ly + (8 if up else -8):.1f}" '
            f'stroke="{color}" stroke-width="2"/>'
            f'<circle cx="{x:.1f}" cy="{axis_y}" r="5.5" fill="{color}" stroke="var(--surface)" stroke-width="2"/>'
        )
        labels.append(
            f'<text class="c-val" x="{x:.1f}" y="{ly:.1f}" text-anchor="middle">{e(s["time"])}</text>'
            f'<text class="c-tick" x="{x:.1f}" y="{ly + (-13 if up else 13):.1f}" text-anchor="middle">'
            f'{e(s["id"])} · плечо {e(s["arm"])}</text>'
        )
    hours = "".join(
        f'<line class="c-grid" x1="{pad_l + hh / 24 * plot:.1f}" y1="{axis_y - 6}" '
        f'x2="{pad_l + hh / 24 * plot:.1f}" y2="{axis_y + 6}"/>'
        f'<text class="c-tick" x="{pad_l + hh / 24 * plot:.1f}" y="{axis_y + 58}" text-anchor="middle">{hh}:00</text>'
        for hh in (0, 6, 12, 18, 24)
    )
    return (
        f'<figure class="figure"><div class="figure__scroll">'
        f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" '
        f'aria-label="Слоты постинга по местному времени и плечам эксперимента">'
        f'<line class="c-axis" x1="{pad_l}" y1="{axis_y}" x2="{w - pad_r}" y2="{axis_y}"/>'
        f'{hours}{"".join(marks)}{"".join(labels)}</svg></div>'
        f'<div class="legend"><span class="legend__item"><i class="sw sw--1"></i>плечо A — прайм-тайм</span>'
        f'<span class="legend__item"><i class="sw sw--2"></i>плечо B — окна низкой конкуренции</span></div>'
        f'<figcaption>Местное время целевого гео. Планировщик переводит в UTC по IANA-таймзоне, '
        f'поэтому переход на зимнее время не сдвигает сетку.</figcaption></figure>'
    )


# ─────────────────────────── стили ───────────────────────────

CSS = """
:root{
  --paper:#EDF0F2; --surface:#F9FAFB; --sunk:#E3E8EC;
  --ink:#0F1418; --ink-soft:#48535E; --ink-mute:#6F7B86;
  --rule:#C7D0D7; --rule-soft:#DBE2E7;
  --accent:#1C4A85; --accent-soft:#E4EBF4;
  --c1:#3E7AB8; --c2:#C08D1C;
  --ok:#0E6459; --warn:#96690A; --stop:#93261A;
  --ok-bg:#DCEBE8; --warn-bg:#F5EBD4; --stop-bg:#F4DEDA; --mute-bg:#E3E8EC;
  --shadow:0 1px 2px rgba(15,20,24,.06), 0 8px 24px -12px rgba(15,20,24,.18);
  --display:"Archivo","Helvetica Neue",Arial,sans-serif;
  --body:"Source Serif 4",Georgia,"Times New Roman",serif;
  --mono:"JetBrains Mono",ui-monospace,"SFMono-Regular",Menlo,monospace;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#0D1216; --surface:#151B21; --sunk:#1B232A;
    --ink:#E8EDF1; --ink-soft:#A7B2BC; --ink-mute:#7B8792;
    --rule:#2A343D; --rule-soft:#222B33;
    --accent:#84B2E6; --accent-soft:#18242F;
    --c1:#4F8AC5; --c2:#B68829;
    --ok:#5FB3A5; --warn:#D9AC4A; --stop:#E0776A;
    --ok-bg:#12251F; --warn-bg:#251E0E; --stop-bg:#2A1614; --mute-bg:#1B232A;
    --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px -14px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --paper:#0D1216; --surface:#151B21; --sunk:#1B232A;
  --ink:#E8EDF1; --ink-soft:#A7B2BC; --ink-mute:#7B8792;
  --rule:#2A343D; --rule-soft:#222B33;
  --accent:#84B2E6; --accent-soft:#18242F;
  --c1:#4F8AC5; --c2:#B68829;
  --ok:#5FB3A5; --warn:#D9AC4A; --stop:#E0776A;
  --ok-bg:#12251F; --warn-bg:#251E0E; --stop-bg:#2A1614; --mute-bg:#1B232A;
  --shadow:0 1px 2px rgba(0,0,0,.5), 0 10px 30px -14px rgba(0,0,0,.7);
}

*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:var(--body); font-size:17px; line-height:1.62;
  -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1060px; margin:0 auto; padding-inline:20px}
.measure{max-width:66ch}
h1,h2,h3,h4{font-family:var(--display); text-wrap:balance; margin:0}
a{color:var(--accent); text-decoration-thickness:1px; text-underline-offset:3px}
:focus-visible{outline:2px solid var(--accent); outline-offset:3px; border-radius:3px}
@media (prefers-reduced-motion:reduce){*{animation:none!important; transition:none!important}}

/* ── шапка ── */
.masthead{border-bottom:1px solid var(--rule); background:var(--surface)}
.masthead__inner{padding-block:44px 30px}
.eyebrow{
  font-family:var(--mono); font-size:11.5px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--ink-mute); margin:0 0 18px
}
.eyebrow b{color:var(--accent); font-weight:500}
h1{font-size:clamp(34px,6.4vw,60px); line-height:1.02; font-weight:700; letter-spacing:-.025em}
h1 em{font-style:normal; color:var(--accent)}
.standfirst{
  font-size:clamp(17px,2.1vw,20px); color:var(--ink-soft); margin:18px 0 0; max-width:60ch
}
.meta{
  display:flex; flex-wrap:wrap; gap:0; margin-top:30px;
  border:1px solid var(--rule); border-radius:8px; overflow:hidden; background:var(--paper)
}
.meta__cell{
  flex:1 1 128px; padding:13px 16px; border-right:1px solid var(--rule-soft)
}
.meta__cell:last-child{border-right:0}
.meta__num{
  font-family:var(--mono); font-size:24px; font-weight:600; color:var(--ink);
  font-variant-numeric:tabular-nums; line-height:1.1
}
.meta__lab{font-family:var(--mono); font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-mute); margin-top:5px}

/* ── навигация ── */
.nav{
  position:sticky; top:0; z-index:20; background:color-mix(in srgb, var(--paper) 92%, transparent);
  backdrop-filter:blur(8px); border-bottom:1px solid var(--rule)
}
.nav__scroll{display:flex; gap:2px; overflow-x:auto; padding-block:9px; scrollbar-width:none}
.nav__scroll::-webkit-scrollbar{display:none}
.nav a{
  flex:0 0 auto; font-family:var(--mono); font-size:11.5px; letter-spacing:.06em; text-transform:uppercase;
  color:var(--ink-soft); text-decoration:none; padding:7px 11px; border-radius:5px; white-space:nowrap
}
.nav a:hover{background:var(--sunk); color:var(--ink)}

/* ── секции ── */
section{padding-block:56px; border-bottom:1px solid var(--rule-soft)}
section:last-of-type{border-bottom:0}
.sec__head{display:flex; gap:14px; align-items:baseline; margin-bottom:8px}
.sec__idx{
  font-family:var(--mono); font-size:12px; color:var(--accent); letter-spacing:.08em;
  border:1px solid var(--accent); border-radius:4px; padding:2px 7px; flex:0 0 auto
}
h2{font-size:clamp(25px,3.6vw,35px); font-weight:700; letter-spacing:-.018em; line-height:1.12}
.sec__lede{color:var(--ink-soft); margin:12px 0 30px; max-width:64ch; font-size:18px}
h3{font-size:20px; font-weight:600; margin:34px 0 10px; letter-spacing:-.008em}
p{margin:0 0 14px}
.small{font-size:15px; color:var(--ink-soft)}

/* ── чипы ── */
.chip{
  display:inline-block; font-family:var(--mono); font-size:10.5px; letter-spacing:.06em;
  text-transform:uppercase; padding:3px 7px; border-radius:4px; white-space:nowrap; font-weight:500
}
.chip--ok{background:var(--ok-bg); color:var(--ok)}
.chip--warn{background:var(--warn-bg); color:var(--warn)}
.chip--stop{background:var(--stop-bg); color:var(--stop)}
.chip--mute{background:var(--mute-bg); color:var(--ink-mute)}

/* ── шаги решений ── */
.steps{display:flex; flex-direction:column; gap:0; counter-reset:s}
.step{
  display:grid; grid-template-columns:54px 1fr; gap:20px;
  padding:24px 0; border-top:1px solid var(--rule-soft)
}
.step:first-child{border-top:1px solid var(--rule)}
.step__n{
  font-family:var(--mono); font-size:13px; font-weight:600; color:var(--accent);
  font-variant-numeric:tabular-nums; padding-top:4px
}
.step h3{margin:0 0 8px; font-size:21px}
.step__why{color:var(--ink-soft); margin:0 0 12px; max-width:72ch}
.step__do{max-width:74ch}
.step__do{
  background:var(--surface); border-left:2px solid var(--accent);
  padding:13px 16px; border-radius:0 6px 6px 0; margin:0 0 10px
}
.step__cost{font-family:var(--mono); font-size:12.5px; color:var(--ink-mute)}

/* ── таблицы ── */
.tablewrap{overflow-x:auto; border:1px solid var(--rule); border-radius:8px; background:var(--surface); margin:0 0 12px}
table{border-collapse:collapse; width:100%; font-size:14.5px; font-family:var(--display)}
th,td{text-align:left; padding:11px 14px; border-bottom:1px solid var(--rule-soft); vertical-align:top}
thead th{
  font-family:var(--mono); font-size:10.5px; letter-spacing:.09em; text-transform:uppercase;
  color:var(--ink-mute); background:var(--sunk); border-bottom:1px solid var(--rule); white-space:nowrap
}
tbody tr:last-child td{border-bottom:0}
td.num{font-family:var(--mono); font-variant-numeric:tabular-nums; white-space:nowrap}
td.code{font-family:var(--mono); font-size:12.5px; color:var(--ink-mute); text-transform:uppercase}
.rowlab{font-weight:600}

/* ── находки ── */
.findings{display:flex; flex-direction:column; gap:0}
.finding{padding:20px 0; border-top:1px solid var(--rule-soft)}
.finding:first-child{border-top:1px solid var(--rule)}
.finding__top{display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin-bottom:9px}
.finding__kind{font-family:var(--mono); font-size:10.5px; letter-spacing:.07em; text-transform:uppercase; color:var(--ink-mute)}
.finding__claim{font-weight:600; font-family:var(--display); font-size:17px; margin:0 0 8px; line-height:1.35}
.finding__body{color:var(--ink-soft); font-size:15.5px; margin:0 0 9px}
.finding__do{font-size:15.5px; margin:0 0 7px}
.finding__do b{font-family:var(--mono); font-size:11px; letter-spacing:.07em; text-transform:uppercase; color:var(--accent); font-weight:500}
.finding__src{font-family:var(--mono); font-size:11.5px; color:var(--ink-mute); word-break:break-word}

/* ── карточки ── */
.cards{display:grid; grid-template-columns:repeat(auto-fit,minmax(250px,1fr)); gap:14px}
.card{background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:18px}
.card h4{font-size:15px; margin:0 0 9px; letter-spacing:-.005em}
.card p{font-size:14.5px; color:var(--ink-soft); margin:0 0 8px}
.card ul{margin:0; padding-left:18px; font-size:14.5px; color:var(--ink-soft)}
.card li{margin-bottom:4px}
.card__tag{font-family:var(--mono); font-size:10.5px; letter-spacing:.09em; text-transform:uppercase; color:var(--ink-mute); display:block; margin-bottom:8px}

/* ── запреты ── */
.bans{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:10px; margin:0 0 18px}
.ban{
  display:flex; gap:11px; align-items:flex-start; background:var(--stop-bg);
  border-radius:7px; padding:13px 15px; font-size:15px
}
.ban svg{flex:0 0 auto; margin-top:3px}
.callout{
  background:var(--surface); border:1px solid var(--rule); border-left:3px solid var(--stop);
  border-radius:0 8px 8px 0; padding:18px 20px; margin:22px 0
}
.callout--ok{border-left-color:var(--ok)}
.callout h4{font-size:16px; margin:0 0 8px}
.callout p{margin:0 0 8px; font-size:15.5px; color:var(--ink-soft)}
.callout p:last-child{margin:0}
.quote{font-family:var(--mono); font-size:13px; color:var(--ink); background:var(--sunk); padding:11px 14px; border-radius:6px; margin:10px 0; overflow-x:auto}

/* ── графики ── */
.figure{margin:26px 0; background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:20px 20px 16px}
.figure__scroll{overflow-x:auto}
.figure svg{max-width:100%; height:auto; display:block}
figcaption{font-size:13.5px; color:var(--ink-mute); margin-top:12px; max-width:62ch}
.c-lab{font-family:var(--display); font-size:13px; font-weight:600; fill:var(--ink)}
.c-val{font-family:var(--mono); font-size:12px; fill:var(--ink-soft); font-variant-numeric:tabular-nums}
.c-tick{font-family:var(--mono); font-size:10.5px; fill:var(--ink-mute); font-variant-numeric:tabular-nums}
.c-grid{stroke:var(--rule-soft); stroke-width:1}
.c-axis{stroke:var(--rule); stroke-width:1.5}
.legend{display:flex; gap:18px; flex-wrap:wrap; margin-top:14px; font-family:var(--mono); font-size:11.5px; color:var(--ink-soft)}
.legend__item{display:flex; align-items:center; gap:7px}
.sw{width:11px; height:11px; border-radius:3px; display:inline-block}
.sw--1{background:var(--c1)} .sw--2{background:var(--c2)}

/* ── подвал ── */
footer{padding-block:40px 60px; color:var(--ink-mute); font-size:14px}
footer p{max-width:70ch}
.kicker{font-family:var(--mono); font-size:11px; letter-spacing:.12em; text-transform:uppercase; color:var(--ink-mute); margin:0 0 10px}

@media (max-width:560px){
  body{font-size:16.5px}
  .step{grid-template-columns:1fr; gap:8px}
  .step__n{padding-top:0}
  .meta__cell{flex:1 1 50%; border-right:0; border-bottom:1px solid var(--rule-soft)}
  section{padding-block:42px}
}
"""


# ─────────────────────────── секции ───────────────────────────

def sec(idx: str, sid: str, title: str, lede: str, body: str) -> str:
    return (f'<section id="{sid}"><div class="wrap">'
            f'<div class="sec__head"><span class="sec__idx">{e(idx)}</span><h2>{e(title)}</h2></div>'
            f'<p class="sec__lede">{lede}</p>{body}</div></section>')


def s_decisions() -> str:
    steps = []
    for i, s in enumerate(R.decision_order(), start=1):
        steps.append(
            f'<div class="step"><div class="step__n">{i:02d}</div><div>'
            f'<h3>{e(s["step"])}</h3>'
            f'<p class="step__why">{e(s["why"])}</p>'
            f'<div class="step__do">{e(s["action"])}</div>'
            f'<div class="step__cost">{e(s["cost"])}</div></div></div>'
        )
    return sec("01", "order", "Порядок решений",
               "Пять решений, из которых первое необратимо, а остальные зависят от него. "
               "Нумерация здесь — не оформление: это последовательность, в которой шаги "
               "нельзя менять местами.",
               f'<div class="steps">{"".join(steps)}</div>')


def s_geo() -> str:
    rows = R.geo_rows()
    body = [chart_prices(rows), '<div class="tablewrap"><table>',
            '<thead><tr><th>Гео</th><th>Приоритет</th><th>Язык</th><th>Топ-игры</th>'
            '<th>Цена/мес</th><th>Точка приёма</th><th>Сленг для хуков</th></tr></thead><tbody>']
    for x in rows:
        price = f'${x["price_lo"]:.2f}–${x["price_hi"]:.2f}' if x["price_lo"] != x["price_hi"] \
            else (f'${x["price"]:.2f}' if x["price"] else "—")
        flags = []
        if x["blocked"]:
            flags.append('<span class="chip chip--stop">платёж заблокирован</span>')
        if x["needs_split"]:
            flags.append('<span class="chip chip--warn">разделить кластер</span>')
        body.append(
            f'<tr><td class="rowlab">{e(x["name"])}<br><span class="code">{e(x["code"])}</span>'
            f'{" " + " ".join(flags) if flags else ""}</td>'
            f'<td class="num">{x["priority"]}</td>'
            f'<td class="code">{e(x["lang"])}</td>'
            f'<td>{e(", ".join(x["games"]))}</td>'
            f'<td class="num">{price}<br><span class="code">{e(x["tier"])}</span></td>'
            f'<td class="code">{e(x["entry"])}</td>'
            f'<td class="small">{e(", ".join(x["slang"][:5]))}</td></tr>'
        )
    body.append("</tbody></table></div>")
    body.append(
        '<div class="callout callout--ok"><h4>Самое дорогое гео — не США</h4>'
        '<p>Саудовская Аравия принимает 21–26 $ за месяц против 9–10 $ в США. Ресерч нашёл '
        'локального лидера рынка, который берёт 149 SAR за 30 дней, и рекомендует заходить чуть '
        'ниже него, а не копировать западный прайс.</p>'
        '<p>Обратная сторона: Ирак с одним из высочайших в мире проникновений TikTok — '
        'страна, которой платёжные системы не дают платить. Показы там оплачивают аудиторию, '
        'которая физически не может купить.</p></div>')
    return sec("02", "geo", "Гео-матрица",
               "Цена подписки, язык контента и точка приёма трафика по каждой стране. "
               "Цены — не пересчёт западного прайса по курсу, а локальные якоря: то, с чем "
               "аудитория сравнивает покупку на своём рынке.",
               "".join(body))


def s_factors() -> str:
    rows = ['<div class="tablewrap"><table><thead><tr><th>Сила</th><th>Фактор</th>'
            '<th>Что показывают данные</th><th>Источник</th></tr></thead><tbody>']
    for f in R.geo_factors():
        rank = f["rank"]
        rank_chip = ('<span class="chip chip--stop">нет влияния</span>' if rank == "—"
                     else f'<span class="chip chip--{"ok" if rank == "S" else "warn"}">{e(rank)}</span>')
        rows.append(f'<tr><td>{rank_chip}</td><td class="rowlab">{e(f["factor"])}</td>'
                    f'<td class="small">{e(f["note"])}</td>'
                    f'<td class="small"><span class="finding__src">{e(f["source"])}</span></td></tr>')
    rows.append("</tbody></table></div>")

    fnd = []
    for f in R.findings("r__geo_targeting_truth", limit=5):
        fnd.append(
            f'<div class="finding"><div class="finding__top">{chip(f.get("confidence"))}'
            f'<span class="finding__kind">{e(R.KIND_LABEL.get(f.get("kind",""), f.get("kind","")))}</span></div>'
            f'<p class="finding__claim">{e(f.get("claim"))}</p>'
            f'<p class="finding__body">{e(str(f.get("evidence"))[:420])}</p>'
            f'<p class="finding__do"><b>вывод</b> {e(str(f.get("actionable"))[:300])}</p>'
            f'<p class="finding__src">{e(str(f.get("source"))[:190])}</p></div>')
    return sec("03", "factors", "Что управляет гео-выдачей",
               "Исходный вопрос был про город прокси: Нью-Йорк или Вашингтон. "
               "Ответ измерен и однозначен — органическая гео-выдача существует только на "
               "уровне страны, а внутри страны не работает ничего.",
               "".join(rows) + f'<h3>Доказательная база</h3><div class="findings">{"".join(fnd)}</div>')


def s_timing() -> str:
    sch = R.d("schedule.json")
    arms = sch.get("experiment_arms", {})
    infra = sch.get("infrastructure_math", {})
    th = sch.get("decision_thresholds", {})
    body = [chart_slots(R.slots())]
    body.append(
        '<div class="callout"><h4>Источники противоречат друг другу сильнее, чем размер эффекта</h4>'
        '<p>Buffer на 7,1 млн постов даёт пик 18:00–23:00 и выходные лучше будней. Sprout Social '
        'на 2 млрд взаимодействий — ровно наоборот: вторник–четверг 14:00–18:00, выходные не постить. '
        'Later на 6 млн постов ставит лучшим временем 05:00.</p>'
        '<p>Причина структурная: на TikTok около 70% просмотров приходит с For You, а Shorts '
        'переподнимаются в выдаче неделями. Просмотры отвязаны от момента публикации — в отличие '
        'от хронологической ленты.</p></div>')
    body.append('<h3>Поэтому расписание проверяется, а не назначается</h3>')
    body.append('<div class="tablewrap"><table><thead><tr><th>Параметр</th><th>Значение</th></tr></thead><tbody>'
                f'<tr><td class="rowlab">Плечо A</td><td class="num">{e(", ".join(arms.get("arm_A_prime") or []))} — прайм-тайм</td></tr>'
                f'<tr><td class="rowlab">Плечо B</td><td class="num">{e(", ".join(arms.get("arm_B_low_competition") or []))} — низкая конкуренция</td></tr>'
                f'<tr><td class="rowlab">Фиксация плеча</td><td class="num">{e(arms.get("freeze_days"))} дней</td></tr>'
                f'<tr><td class="rowlab">Минимум постов на плечо</td><td class="num">{e(arms.get("min_posts_per_arm_before_verdict"))}</td></tr>'
                f'<tr><td class="rowlab">Метрика сравнения</td><td class="num">медиана просмотров</td></tr>'
                f'<tr><td class="rowlab">Мёртвая зона</td><td class="num">02:00–04:59 местного</td></tr>'
                f'<tr><td class="rowlab">Первый съём метрик</td><td class="num">{e(th.get("metrics_first_pull_h"))} ч после публикации</td></tr>'
                '</tbody></table></div>')
    body.append('<h3>Математика инфраструктуры</h3>'
                '<div class="tablewrap"><table><thead><tr><th>Ограничение</th><th>Значение</th><th>Следствие</th></tr></thead><tbody>'
                f'<tr><td class="rowlab">YouTube: загрузок в сутки</td><td class="num">{e(infra.get("youtube_videos_insert_per_project_per_day"))} на проект Google Cloud</td>'
                f'<td class="small">{e(infra.get("youtube_example"))}</td></tr>'
                f'<tr><td class="rowlab">TikTok: пауза между вызовами</td><td class="num">{e(infra.get("tiktok_min_seconds_between_calls_per_account"))} с на аккаунт</td>'
                '<td class="small">Планирования через API нет — очередь и таймер держит свой планировщик</td></tr>'
                '<tr><td class="rowlab">Instagram: квота</td><td class="num">4800 × показы за сутки</td>'
                '<td class="small">У аккаунта без показов квоты API нет вообще: новый аккаунт физически не может публиковаться через API</td></tr>'
                '</tbody></table></div>')
    return sec("04", "timing", "Тайминги",
               "Время публикации — фактор третьего порядка. Разница между плохим и хорошим хуком "
               "больше, чем между плохим и хорошим временем, поэтому сетка каналов здесь работает "
               "как измерительный инструмент.",
               "".join(body))


def s_content() -> str:
    loc = R.d("local_tactics.json").get("by_geo", {})
    names = {"es": "Испанский / LatAm", "br": "Бразилия", "ar_gulf": "Залив",
             "ar_egypt_iraq": "Египет и Ирак", "id": "Индонезия"}
    cards = []
    for key, v in loc.items():
        if key.startswith("_"):
            continue
        bits = []
        for label, field in (("жанр", "local_genre"), ("миф", "local_myth"),
                             ("аудитория", "audience"), ("деньги", "money_note"),
                             ("площадка", "extra_platform"), ("контент", "content_note"),
                             ("продукт", "product_note"), ("стратегия", "strategy_note"),
                             ("расписание", "schedule_note"), ("разделение", "split_rule")):
            if v.get(field):
                bits.append(f'<p><b>{label}.</b> {e(str(v[field])[:340])}</p>')
        terms = v.get("local_terms") or v.get("hooks") or []
        if terms:
            bits.append('<p class="small"><b>лексика для хуков:</b> '
                        + e(", ".join(str(t) for t in terms[:8])) + "</p>")
        if v.get("proof"):
            bits.append(f'<p class="finding__src">{e(str(v["proof"])[:260])}</p>')
        cards.append(f'<div class="card"><span class="card__tag">{e(names.get(key, key))}</span>'
                     + "".join(bits) + "</div>")

    limits = R.d("platform_limits.json")
    tt = limits.get("tiktok", {})
    hashtag = tt.get("hashtag_effect", {})
    cta = tt.get("cta_effect", {})
    decay = limits.get("_meta", {}).get("organic_decay_baseline", {})
    rules = ('<div class="tablewrap"><table><thead><tr><th>Правило</th><th>Число</th><th>Откуда</th></tr></thead><tbody>'
             f'<tr><td class="rowlab">Хештегов на пост</td><td class="num">1–2, максимум {e(tt.get("hashtags_hard_max"))}</td>'
             f'<td class="small">{e(hashtag.get("optimum"))}</td></tr>'
             f'<tr><td class="rowlab">Трафик с хештегов</td><td class="num">{e(hashtag.get("hashtag_traffic_yoy"))} год к году</td>'
             f'<td class="small">{e(hashtag.get("posts_with_hashtags"))}</td></tr>'
             f'<tr><td class="rowlab">CTA-вопрос в подписи</td><td class="num">+26% комментариев</td>'
             f'<td class="small">{e(cta.get("consequence"))}</td></tr>'
             f'<tr><td class="rowlab">Падение органики</td><td class="num">просмотры −31%</td>'
             f'<td class="small">{e(decay.get("planning_rule"))}</td></tr>'
             f'<tr><td class="rowlab">Бесполезные теги</td><td class="num">#fyp #viral #parati</td>'
             '<td class="small">Охвата не добавляют; блоклист зашит в генератор подписей</td></tr>'
             '</tbody></table></div>')

    bank = R.d("content_bank.json")
    hooks = R.load(R.DATA / "hooks_expanded.json")
    stat = (f'<p class="small">В банке {len(bank.get("formats") or [])} форматов и '
            f'{hooks.get("count", 0)} готовых хуков, размноженных по гео: у каждой страны свои игры '
            f'и свой сленг. Числа FPS в хуке всегда идут с моделью железа — иначе обещание '
            f'непроверяемо и блокируется валидатором.</p>')
    return sec("05", "content", "Контент и локальные тактики",
               "Главная находка блока: в каждой языковой тусовке есть свои жанры и своя лексика, "
               "которых нет в англоязычных гайдах. Это то, что отличает местный канал от переводного.",
               f'<div class="cards">{"".join(cards)}</div>'
               f'<h3>Правила, которые вытекают из цифр</h3>{rules}{stat}')


def s_product() -> str:
    off = R.d("offers.json")
    prod = off.get("product", {})
    rules = off.get("claim_rules", {})
    caps = rules.get("numeric_caps", {})
    tiers = rules.get("honest_tiers", {})
    x_icon = ('<svg width="15" height="15" viewBox="0 0 16 16" aria-hidden="true">'
              '<path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" stroke-width="2" '
              'stroke-linecap="round" fill="none"/></svg>')
    bans = "".join(f'<div class="ban">{x_icon}<span>{e(b)}</span></div>'
                   for b in prod.get("what_it_never_does", []))
    cap_rows = ('<div class="tablewrap"><table><thead><tr><th>Обещание</th><th>Потолок</th></tr></thead><tbody>'
                f'<tr><td class="rowlab">Прирост среднего FPS</td><td class="num">+{e(caps.get("max_claimed_avg_fps_gain_pct"))}%</td></tr>'
                f'<tr><td class="rowlab">Прирост 1% low</td><td class="num">+{e(caps.get("max_claimed_1pct_low_gain_pct"))}% (с указанием фоновой нагрузки)</td></tr>'
                f'<tr><td class="rowlab">Снижение латентности</td><td class="num">−{e(caps.get("max_claimed_latency_reduction_ms"))} ms</td></tr>'
                '<tr><td class="rowlab">Снижение пинга</td><td class="num">запрещено полностью</td></tr>'
                '</tbody></table></div>')
    tier_cards = "".join(
        f'<div class="card"><span class="card__tag">{lab}</span><ul>'
        + "".join(f"<li>{e(x)}</li>" for x in (tiers.get(key) or [])) + "</ul></div>"
        for key, lab in (("tier_a_measured_sellable", "работает и измерено"),
                         ("tier_b_noise", "шум ±0–3%"),
                         ("tier_c_snake_oil", "снейк-ойл")))
    fnd = []
    for f in R.findings("r__anticheat_safety", limit=4):
        fnd.append(f'<div class="finding"><div class="finding__top">{chip(f.get("confidence"))}'
                   f'<span class="finding__kind">{e(R.KIND_LABEL.get(f.get("kind",""), ""))}</span></div>'
                   f'<p class="finding__claim">{e(f.get("claim"))}</p>'
                   f'<p class="finding__body">{e(str(f.get("evidence"))[:380])}</p>'
                   f'<p class="finding__src">{e(str(f.get("source"))[:180])}</p></div>')
    return sec("06", "product", "Продукт: запреты и потолки обещаний",
               "Ни один мейджорный античит не банит за твики Windows. Риск в другом: античиты "
               "требуют Secure Boot, TPM и IOMMU, а классические твикеры именно их и отключают. "
               "Клиент, которому продукт выключил Secure Boot, не запустит игру.",
               f'<h3>Чего продукт не делает никогда</h3><div class="bans">{bans}</div>'
               f'<div class="callout"><h4>Прецедент по ассортименту</h4>'
               f'<p>IObit Advanced SystemCare — прямой аналог «оптимизатора ПК» — уже находится в '
               f'публичном denylist драйверов EA Javelin. Класс «оптимизаторов с драйвером» в чёрных '
               f'списках целиком, поэтому в продукте не может быть драйвера уровня ядра ни в каком виде.</p></div>'
               f'<h3>Что из твиков реально работает</h3><div class="cards">{tier_cards}</div>'
               f'<h3>Потолки обещаний в контенте</h3>{cap_rows}'
               f'<p class="small">Проверка встроена в конвейер: текст, нарушающий потолок или дающий '
               f'число FPS без модели железа, не доходит до рендера.</p>'
               f'<h3>Доказательная база по античитам</h3><div class="findings">{"".join(fnd)}</div>')


def s_payments() -> str:
    pay = R.d("payments.json")
    rails = pay.get("rails", {})
    prim = rails.get("primary_recommended", {})
    a = prim.get("option_A_foreign_entity_stripe", {})
    b = prim.get("option_B_lemon_squeezy", {})
    forb = rails.get("forbidden", {})
    cb = pay.get("chargeback_guardrails", {})
    blocked = pay.get("blocked_buyer_countries", {})
    sec2 = rails.get("secondary", {})
    crypto = sec2.get("crypto", {})

    table = ('<div class="tablewrap"><table><thead><tr><th>Рельс</th><th>Статус</th><th>Стоимость</th>'
             '<th>Замечание</th></tr></thead><tbody>'
             f'<tr><td class="rowlab">Иностранное юрлицо + Stripe</td>'
             f'<td><span class="chip chip--ok">основной</span></td>'
             f'<td class="num small">{e(a.get("cost"))}</td>'
             f'<td class="small">{e(a.get("precedent"))}</td></tr>'
             f'<tr><td class="rowlab">Lemon Squeezy</td>'
             f'<td><span class="chip chip--ok">основной</span></td>'
             f'<td class="num small">{e(b.get("fees"))}</td>'
             f'<td class="small">Выплаты на банк: {e(", ".join(b.get("available_payout_countries") or []))}. '
             f'Недоступно: {e(", ".join(b.get("not_available") or []))}</td></tr>'
             f'<tr><td class="rowlab">PayPal</td>'
             f'<td><span class="chip chip--warn">дополнительный</span></td>'
             f'<td class="num small">{e(sec2.get("paypal", {}).get("fees"))}</td>'
             f'<td class="small">{e(sec2.get("paypal", {}).get("verification_status"))}</td></tr>'
             f'<tr><td class="rowlab">Крипта</td>'
             f'<td><span class="chip chip--warn">дополнительный</span></td>'
             f'<td class="num small">{e(crypto.get("providers_fee"))}</td>'
             f'<td class="small">{e(crypto.get("expected_share_of_checkouts"))} чекаутов. {e(crypto.get("why_low"))}</td></tr>'
             f'<tr><td class="rowlab">Paddle</td>'
             f'<td><span class="chip chip--stop">исключить</span></td><td class="num small">—</td>'
             f'<td class="small">{e(forb.get("paddle", {}).get("why"))}</td></tr>'
             f'<tr><td class="rowlab">Gumroad</td>'
             f'<td><span class="chip chip--stop">риск</span></td><td class="num small">10% + $0.50</td>'
             f'<td class="small">{e(forb.get("gumroad", {}).get("why"))}</td></tr>'
             '</tbody></table></div>')

    return sec("07", "payments", "Платежи",
               "Этот блок решается первым и назад не отматывается: страна юрлица фиксируется "
               "навсегда при первом живом платеже, а Stripe не работает ни в одной стране СНГ.",
               table
               + f'<div class="callout"><h4>Математика споров при низком чеке</h4>'
                 f'<p>{e(cb.get("practical_meaning"))}. Visa флагует несоответствие при доле споров '
                 f'{cb.get("visa_vamp_noncompliant", {}).get("ratio", 0) * 100:.1f}% и всего '
                 f'{e(cb.get("visa_vamp_noncompliant", {}).get("count_per_month"))} спорах в месяц, '
                 f'а сам спор стоит в 1,5–4 раза дороже транзакции.</p>'
                 f'<p>Отсюда обязательные вещи: 3DS выше 10% объёма Mastercard, явное описание в '
                 f'выписке на странице благодарности и в письме, пакет доказательств на каждый заказ.</p></div>'
               + f'<h3>Страны, которым платёжки не дают платить</h3>'
                 f'<div class="quote">{e(" · ".join(blocked.get("codes") or []))}</div>'
                 f'<p class="small">{e(blocked.get("traffic_rule"))}</p>'
                 f'<div class="callout"><h4>Стиль маркетинга — часть комплаенса</h4>'
                 f'<p>Stripe прямо называет запрещёнными «outrageous claims», «deceptive testimonials», '
                 f'«high-pressure upselling» и «suspicious remote technical support». То есть валидатор '
                 f'обещаний защищает не репутацию, а сам платёжный рельс.</p></div>')


def s_platforms() -> str:
    L = R.d("platform_limits.json")
    names = {"tiktok": "TikTok", "youtube": "YouTube Shorts", "instagram": "Instagram Reels"}
    rows = ['<div class="tablewrap"><table><thead><tr><th>Площадка</th><th>Постов в сутки</th>'
            '<th>Длина</th><th>Хештеги</th><th>Что решает всё</th></tr></thead><tbody>']
    notes = {
        "tiktok": "До аудита приложения API публикует только приватно — публичного авто-залива "
                  "через официальный путь нет. 6 запросов в минуту на токен.",
        "youtube": "100 загрузок в сутки на проект Google Cloud, а не на канал. Уникальность "
                   "заголовка и описания требуется по всей сети. Музыкальный трек режет выручку вдвое.",
        "instagram": "Квота = 4800 × показы за сутки: у нового аккаунта её нет. Файл не загрузить — "
                     "только публичная ссылка. Оригинальность требует экранного присутствия автора.",
    }
    for k, label in names.items():
        p = L.get(k, {})
        v = p.get("video", {})
        sweet = v.get("sweet_spot_s") or []
        rows.append(
            f'<tr><td class="rowlab">{e(label)}</td>'
            f'<td class="num">{e(p.get("max_posts_per_day"))} · на прогреве {e(p.get("warming_posts_per_day"))}</td>'
            f'<td class="num">{e(sweet[0] if sweet else "?")}–{e(sweet[1] if len(sweet) > 1 else "?")} с</td>'
            f'<td class="num">{e(p.get("recommended_hashtags"))}</td>'
            f'<td class="small">{e(notes.get(k, ""))}</td></tr>')
    rows.append("</tbody></table></div>")

    net = R.r("r__network_architecture")
    mono = L.get("youtube", {}).get("monetization_reality", {})
    orig = L.get("instagram", {}).get("originality_requirement", {})
    body = "".join(rows)
    body += (f'<div class="callout"><h4>Монетизация сети невозможна</h4>'
             f'<p>{e(mono.get("shorts_creator_pool_from_2027_02_01"))} — таково требование к выплатам '
             f'с 1 февраля 2027 года. {e(mono.get("consequence"))}</p></div>')
    body += (f'<div class="callout"><h4>Instagram против безликой сетки</h4>'
             f'<p>{e(orig.get("rule"))}</p><p>{e(orig.get("consequence"))}</p>'
             f'<p class="finding__src">Ранжирующий сигнал: {e(orig.get("ranking_signal"))}</p></div>')
    if net.get("summary"):
        axes = str(net["summary"])
        body += (f'<h3>Оси деления сети</h3><p class="small">{e(axes[axes.find("2)"):axes.find("3)")][:700] if "2)" in axes else axes[:700])}</p>')
    body += ('<div class="quote">TikTok: «create only one account for strictly personal purposes» · '
             'Meta: «Create only one account (your own)»</div>'
             '<p class="small">За квартал TikTok снял более 86 млн фейковых аккаунтов. Это цифра для '
             'планирования расходной части, а не аргумент в споре о правилах.</p>')
    return sec("08", "platforms", "Лимиты площадок",
               "Технические потолки, которые определяют архитектуру, а не пожелания. Операционные "
               "лимиты в системе выставлены ниже технических: предел площадки не равен безопасному "
               "темпу для нового аккаунта.",
               body)


def s_gaps() -> str:
    reps = R.reports()
    st = R.stats()
    gaps = []
    for name, v in sorted(reps.items()):
        if not isinstance(v, dict):
            continue
        for q in (v.get("open_questions") or [])[:2]:
            if isinstance(q, str) and len(q) > 30:
                gaps.append((name.replace("r__", "").replace("geo__", "гео "), q))
    gaps = gaps[:12]
    items = "".join(
        f'<tr><td class="code">{e(n)}</td><td class="small">{e(q[:300])}</td></tr>' for n, q in gaps)
    pending = ("Прогон ещё идёт: часть страновых агентов (Великобритания, Польша, Турция, Индонезия, "
               "Филиппины, Вьетнам, Индия, Япония, Корея, Бразилия, СНГ) и часть тематических "
               "(прокси-инфраструктура, API автопостинга, покупные аккаунты, железная линейка, кейсы) "
               "не завершены. Отчёт пересобирается из данных, поэтому по мере готовности эти разделы "
               "дополняются без переписывания.")
    honest = ('<div class="callout"><h4>Где данных нет и это признано</h4>'
              '<p>Практический опыт операторов сетей — сколько каналов из двадцати взлетает, реальный '
              'burn rate аккаунтов, предел одного оператора — подтвердить не удалось: поисковые '
              'бюджеты агентов упирались в лимиты, а альтернативные поисковики отдавали капчу. Эти '
              'пункты помечены как неподтверждённые, а не заполнены правдоподобными числами.</p>'
              '<p>То же с эффектом платного «разгона» гео: официально подтверждена только атрибуция '
              'платной вовлечённости органическому посту в Spark Ads. Что платная вовлечённость '
              'является входом органического ранжирования, не подтверждает ни одна площадка.</p></div>')
    return sec("09", "gaps", "Чего в данных нет",
               f"Из {st['findings']} находок часть помечена как неподтверждённая. "
               f"Этот раздел существует, чтобы отличать измеренное от предположительного.",
               honest
               + (f'<h3>Открытые вопросы из отчётов</h3><div class="tablewrap"><table><thead><tr>'
                  f'<th>Блок</th><th>Вопрос</th></tr></thead><tbody>{items}</tbody></table></div>' if items else "")
               + f'<p class="small">{e(pending)}</p>')


def build() -> str:
    st = R.stats()
    nav = [("01", "order", "Порядок решений"), ("02", "geo", "Гео-матрица"),
           ("03", "factors", "Гео-факторы"), ("04", "timing", "Тайминги"),
           ("05", "content", "Контент"), ("06", "product", "Продукт"),
           ("07", "payments", "Платежи"), ("08", "platforms", "Лимиты"),
           ("09", "gaps", "Пробелы")]
    nav_html = "".join(f'<a href="#{sid}">{idx} {e(label)}</a>' for idx, sid, label in nav)
    meta = [
        (st["countries"], "стран разобрано"),
        (st["topics"], "тематических блоков"),
        (st["findings"], "находок с источниками"),
        (st["sources"], "уникальных источников"),
    ]
    meta_html = "".join(
        f'<div class="meta__cell"><div class="meta__num">{n}</div>'
        f'<div class="meta__lab">{e(lab)}</div></div>' for n, lab in meta)

    return f"""<title>Гео-досье трафика</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700&family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&family=JetBrains+Mono:wght@400;500;600&display=swap">
<style>{CSS}</style>

<header class="masthead"><div class="wrap masthead__inner">
  <p class="eyebrow">Досье · сентябрь 2026 · <b>подписка на твики для геймеров</b></p>
  <h1>Куда лить трафик<br>и <em>чего это стоит</em></h1>
  <p class="standfirst">Разбор гео, площадок, цен и запретов для сети коротких видео, которая
  ведёт трафик на платную подписку. Каждое утверждение — с уровнем доверия и источником.</p>
  <div class="meta">{meta_html}</div>
</div></header>

<nav class="nav" aria-label="Разделы"><div class="wrap nav__scroll">{nav_html}</div></nav>

<main>
{s_decisions()}
{s_geo()}
{s_factors()}
{s_timing()}
{s_content()}
{s_product()}
{s_payments()}
{s_platforms()}
{s_gaps()}
</main>

<footer><div class="wrap">
  <p class="kicker">как читать</p>
  <p>Чипы достоверности означают разное. «Подтверждено» — официальная документация площадки или
  воспроизводимое измерение. «Вероятно» — индустриальные данные без первичного источника.
  «Не подтверждено» — оценка, которую нужно проверять на своих цифрах.</p>
  <p>Числа в отчёте — рабочие значения для решений, а не гарантии. Цены и лимиты площадок
  меняются; каждое такое значение в исходных данных хранится вместе с источником и датой,
  чтобы его можно было перепроверить, а не принимать на веру.</p>
</div></footer>
"""


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    html_out = build()
    OUT.write_text(html_out, encoding="utf-8")
    print(f"{OUT}: {len(html_out)} символов, {OUT.stat().st_size} байт")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
