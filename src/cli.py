#!/usr/bin/env python3
"""CLI оркестратора. Один вход для всех операций — см. ops/RUNBOOK.md.

Типовой цикл:
    python -m src.cli doctor
    python -m src.cli init-grid
    python -m src.cli assets scan
    python -m src.cli plan --days 7
    python -m src.cli render --limit 40
    python -m src.cli publish
    python -m src.cli import-metrics analytics.csv
    python -m src.cli review
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import channel_grid, content_bank, geos, offers, platform_limits, schedule, settings
from .models import (Account, Asset, ChannelSlot, JobState, Platform, PublishMode,
                     VideoPlan, utcnow)
from .planner import plan_days, review_slots
from .publishers import PublishContext, get_publisher
from .render import RenderError, probe_duration, render
from .store import Store
from .tracker import geo_accuracy_report, import_metrics_csv

ASSET_INDEX = Path("data/assets.json")


def _store() -> Store:
    return Store(settings().state_db)


# ---------- doctor ----------

def cmd_doctor(args) -> int:
    cfg = settings()
    problems: list[str] = []
    print("== окружение ==")
    for bin_name in (cfg.ffmpeg, cfg.ffprobe):
        found = shutil.which(bin_name)
        print(f"  {bin_name}: {found or 'НЕ НАЙДЕН'}")
        if not found:
            problems.append(f"нет {bin_name} — рендер не заработает")
    print(f"  dry_run: {cfg.dry_run}")
    print(f"  state_db: {cfg.state_db}")

    print("== данные ==")
    for name, loader in (("geos.json", geos), ("schedule.json", schedule),
                         ("platform_limits.json", platform_limits),
                         ("content_bank.json", content_bank),
                         ("channels.json", channel_grid), ("offers.json", offers)):
        try:
            data = loader()
            size = len(data) if hasattr(data, "__len__") else "?"
            print(f"  {name}: ok ({size} записей верхнего уровня)")
        except Exception as e:
            print(f"  {name}: ОШИБКА — {e}")
            problems.append(f"{name}: {e}")

    active = [g for g in geos().values() if g.get("priority", 9) <= 3]
    print(f"== гео ==\n  активных: {len(active)} -> {', '.join(g['code'] for g in active) or '—'}")
    bank = content_bank()
    print(f"== контент ==\n  форматов: {len(bank.get('formats', []))}, хуков: {len(bank.get('hooks', []))}")

    if problems:
        print("\nНЕ ГОТОВО:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nвсё на месте")
    return 0


# ---------- сетка каналов ----------

def cmd_init_grid(args) -> int:
    st = _store()
    grid = channel_grid()
    created = 0
    for geo_code, geo in geos().items():
        if geo.get("priority", 9) > 3 and not args.all_geos:
            continue
        for platform_name, slots in grid.get("per_platform", {}).items():
            taken_games: set[str] = set()
            for i, tmpl in enumerate(slots, start=1):
                slot_id = f"{geo_code}-{grid['platform_codes'][platform_name]}-{i:02d}"
                token = f"{geo_code}{grid['platform_codes'][platform_name]}{i:02d}"
                game = _resolve_game(tmpl, geo, taken_games)
                if game and tmpl.get("game_rank"):
                    taken_games.add(game)
                theme = (tmpl.get("theme_pattern") or tmpl["theme"]).format(game=game or "PC")
                bio_tmpl = tmpl.get("bio_pattern") or tmpl.get("bio") or ""
                handle = (tmpl.get("handle_pattern") or "{geo}{n}").format(
                    geo=geo_code, n=i, game=(game or "fps").lower().replace(" ", "")
                )
                st.upsert_slot(ChannelSlot(
                    slot_id=slot_id, geo=geo_code, platform=Platform(platform_name),
                    theme=theme, target_game=game,
                    content_formats=tmpl.get("formats", []),
                    handle=handle,
                    bio=bio_tmpl.format(cta=geo.get("entry_point", "link in bio"), game=game or "PC"),
                    persona=tmpl.get("persona", "faceless"),
                    posts_per_day=int(tmpl.get("posts_per_day", 2)),
                    publish_mode=PublishMode(tmpl.get("publish_mode", "kit")),
                    attribution_token=token,
                    # 50/50 по чётности номера слота: половина сетки живёт в прайме,
                    # половина в окнах низкой конкуренции — это и есть эксперимент
                    arm="A" if i % 2 == 1 else "B",
                ))
                created += 1
    print(f"слотов записано: {created}")
    return 0


def _resolve_game(tmpl: dict, geo: dict, taken: set[str]) -> str | None:
    """Какая игра достаётся слоту в этом гео.

    Игровой слот занимает игру по её месту в geos.json -> top_games этого гео:
    канал про популярную здесь игру сильнее канала про игру, в которую тут не
    играют, — и хуков под неё в банке больше. Если у гео игр меньше, чем игровых
    слотов, добираем из общего списка. Внутри одного гео и платформы игра не
    повторяется: два канала про одну игру каннибализируют друг друга.
    """
    rank = tmpl.get("game_rank")
    if not rank:
        return tmpl.get("target_game")

    for candidate in (
        (geo.get("top_games") or [])[rank - 1:rank],     # своё место в топе гео
        [tmpl.get("target_game")],                        # игра из шаблона
        geo.get("top_games") or [],                       # любая из топа гео
        content_bank().get("games", []),                   # общий список
    ):
        for g in candidate:
            if g and g not in taken:
                return g
    return tmpl.get("target_game")


def cmd_slots(args) -> int:
    st = _store()
    rows = st.slots(geo=args.geo, platform=Platform(args.platform) if args.platform else None)
    for s in rows:
        acc = st.account_for_slot(s.slot_id)
        print(f"{s.slot_id:18} {s.platform.value:10} {s.geo:6} {s.publish_mode.value:6} "
              f"{(acc.username if acc else '—'):22} {s.theme}")
    print(f"\nитого: {len(rows)}")
    return 0


def cmd_account_add(args) -> int:
    st = _store()
    st.upsert_account(Account(
        account_id=args.account_id, slot_id=args.slot, platform=Platform(args.platform),
        username=args.username, created_at=utcnow(), credential_ref=args.cred,
        proxy_ref=args.proxy, device_ref=args.device, state=args.state,
        daily_cap=args.cap,
    ))
    print(f"аккаунт {args.account_id} привязан к слоту {args.slot}")
    return 0


def cmd_account_state(args) -> int:
    _store().set_account_state(args.account_id, args.state, args.note or "")
    print(f"{args.account_id} -> {args.state}")
    return 0


# ---------- ассеты ----------

def cmd_assets_scan(args) -> int:
    cfg = settings()
    root = Path(args.dir or cfg.assets_dir)
    exts = {".mp4", ".mov", ".mkv", ".webm", ".mp3", ".wav", ".m4a"}
    items = []
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() not in exts or not p.is_file():
            continue
        kind = "music" if p.suffix.lower() in {".mp3", ".wav", ".m4a"} else "gameplay"
        parts = [x.lower() for x in p.parts]
        game = next((g for g in _known_games() if g.lower().replace(" ", "") in "".join(parts)), None)
        dur = None
        if shutil.which(cfg.ffprobe):
            try:
                dur = round(probe_duration(str(p)), 2)
            except RenderError:
                dur = None
        items.append({"asset_id": p.stem, "path": str(p), "kind": kind,
                      "game": game, "duration_s": dur, "tags": [], "rights": "own"})
    ASSET_INDEX.parent.mkdir(parents=True, exist_ok=True)
    ASSET_INDEX.write_text(json.dumps({"assets": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"найдено ассетов: {len(items)} -> {ASSET_INDEX}")
    return 0


def _known_games() -> list[str]:
    out: set[str] = set()
    for g in geos().values():
        out.update(g.get("top_games", []))
    out.update(content_bank().get("games", []))
    return sorted(out)


def _load_assets() -> list[Asset]:
    if not ASSET_INDEX.exists():
        return []
    raw = json.loads(ASSET_INDEX.read_text(encoding="utf-8"))
    return [Asset(**a) for a in raw.get("assets", [])]


# ---------- план / рендер / публикация ----------

def cmd_plan(args) -> int:
    st = _store()
    assets = _load_assets()
    if not assets:
        print("нет ассетов: сначала `assets scan`. План строится, но рендерить будет нечего.")
    plans = plan_days(st, assets, days=args.days,
                      geo_filter=args.geo.split(",") if args.geo else None)
    by_geo: dict[str, int] = {}
    for p in plans:
        by_geo[p.geo] = by_geo.get(p.geo, 0) + 1
    print(f"запланировано видео: {len(plans)} на {args.days} дн.")
    for g, n in sorted(by_geo.items(), key=lambda kv: -kv[1]):
        print(f"  {g}: {n}")
    return 0


def cmd_render(args) -> int:
    st = _store()
    assets = {a.asset_id: a for a in _load_assets()}
    music = [a for a in assets.values() if a.kind == "music"]
    todo = st.plans_due(until_utc=(datetime.now(timezone.utc) + timedelta(days=args.horizon)).isoformat(),
                        state=JobState.PLANNED)[: args.limit]
    ok = fail = 0
    for row in todo:
        plan = VideoPlan(
            plan_id=row["plan_id"], slot_id=row["slot_id"], geo=row["geo"],
            platform=Platform(row["platform"]), format_id=row["format_id"],
            hook_text=row["hook_text"], body_beats=json.loads(row["body_beats"] or "[]"),
            cta_text=row["cta_text"] or "", caption=row["caption"] or "",
            title=row["title"] or "", hashtags=json.loads(row["hashtags"] or "[]"),
            asset_ids=json.loads(row["asset_ids"] or "[]"),
            variant_seed=row["variant_seed"] or 0,
            target_duration_s=row["target_duration_s"] or 18.0,
            scheduled_for_utc=row["scheduled_for_utc"], state=JobState.PLANNED,
        )
        clips = [assets[a] for a in plan.asset_ids if a in assets]
        if not clips:
            st.set_plan_state(plan.plan_id, JobState.SKIPPED)
            st.log("warn", "render", f"{plan.plan_id}: нет ассетов")
            fail += 1
            continue
        track = music[plan.variant_seed % len(music)] if music else None
        try:
            rr = render(plan, clips, track)
        except RenderError as e:
            st.set_plan_state(plan.plan_id, JobState.FAILED)
            st.log("error", "render", f"{plan.plan_id}: {e}")
            fail += 1
            continue
        if rr.checksum != "dry-run" and st.checksum_seen(rr.checksum):
            st.log("warn", "render", f"{plan.plan_id}: идентичный файл уже существует, пересобери seed")
        st.save_render(rr)
        st.set_plan_state(plan.plan_id, JobState.RENDERED)
        st.mark_asset_used(plan.asset_ids, plan.slot_id)
        ok += 1
    print(f"отрендерено: {ok}, пропущено/ошибок: {fail}")
    return 0


def cmd_publish(args) -> int:
    st = _store()
    until = args.until or datetime.now(timezone.utc).isoformat()
    due = st.plans_due(until_utc=until, state=JobState.RENDERED)[: args.limit]
    today = datetime.now(timezone.utc).date().isoformat()
    counts = {"published": 0, "queued": 0, "skipped": 0, "failed": 0, "waiting_account": 0}
    for row in due:
        slot_id = row["slot_id"]
        slot = next((s for s in st.slots(active_only=False) if s.slot_id == slot_id), None)
        acct = st.account_for_slot(slot_id)
        if not slot:
            st.set_plan_state(row["plan_id"], JobState.SKIPPED)
            st.log("warn", "publish", f"{row['plan_id']}: слот {slot_id} не найден")
            counts["skipped"] += 1
            continue
        if not acct:
            # аккаунта ещё нет — план остаётся в RENDERED и уйдёт, как только аккаунт появится
            st.log("info", "publish", f"{slot_id}: нет привязанного аккаунта, план ждёт")
            counts["waiting_account"] = counts.get("waiting_account", 0) + 1
            continue
        cap = min(acct.daily_cap, int(platform_limits().get(row["platform"], {}).get("max_posts_per_day", 3)))
        if st.posts_today(acct.account_id, today) >= cap:
            st.log("info", "publish", f"{acct.account_id}: дневной лимит {cap} исчерпан")
            counts["skipped"] += 1
            continue
        rend = st.render_for(row["plan_id"])
        if not rend:
            counts["skipped"] += 1
            continue
        plan = VideoPlan(
            plan_id=row["plan_id"], slot_id=slot_id, geo=row["geo"],
            platform=Platform(row["platform"]), format_id=row["format_id"],
            hook_text=row["hook_text"], cta_text=row["cta_text"] or "",
            caption=row["caption"] or "", title=row["title"] or "",
            hashtags=json.loads(row["hashtags"] or "[]"),
            scheduled_for_utc=row["scheduled_for_utc"],
        )
        from .models import RenderResult
        rr = RenderResult(plan_id=rend["plan_id"], video_path=rend["video_path"],
                          thumb_path=rend["thumb_path"], duration_s=rend["duration_s"],
                          width=rend["width"], height=rend["height"],
                          checksum=rend["checksum"], rendered_at=rend["rendered_at"])
        pub = get_publisher(plan.platform, slot.publish_mode, acct)
        res = pub.publish(PublishContext(plan=plan, render=rr, account=acct,
                                         dry_run=settings().dry_run,
                                         public_video_url=args.public_url))
        st.save_post(res)
        st.set_plan_state(plan.plan_id, res.state)
        if res.state == JobState.PUBLISHED:
            counts["published"] += 1
        elif res.state == JobState.QUEUED:
            counts["queued"] += 1
        elif res.state in (JobState.BLOCKED, JobState.NEEDS_HUMAN):
            counts["failed"] += 1
            st.set_account_state(acct.account_id, "limited", res.error or res.state.value)
        else:
            counts["failed"] += 1
    print(json.dumps(counts, ensure_ascii=False))
    return 0


def cmd_record_post(args) -> int:
    """Фиксация ручной публикации (режим KIT), иначе метрики не привяжутся."""
    from .models import PostResult
    st = _store()
    row = next((p for p in st.plans_due(until_utc="9999", state=JobState.QUEUED)
                if p["plan_id"] == args.plan_id), None)
    acct_id = args.account_id
    st.save_post(PostResult(plan_id=args.plan_id, account_id=acct_id,
                            platform=Platform(args.platform), state=JobState.PUBLISHED,
                            remote_id=args.remote_id, remote_url=args.url,
                            published_at=args.at or utcnow(), mode=PublishMode.KIT))
    st.set_plan_state(args.plan_id, JobState.PUBLISHED)
    print(f"зафиксировано: {args.plan_id} -> {args.url or args.remote_id}")
    return 0


# ---------- аналитика ----------

def cmd_import_metrics(args) -> int:
    n = import_metrics_csv(_store(), args.path)
    print(f"импортировано строк: {n}")
    return 0


def cmd_review(args) -> int:
    st = _store()
    buckets = review_slots(st, days=args.days)
    for name in ("scale", "keep", "kill", "too_early"):
        rows = buckets.get(name, [])
        print(f"\n== {name.upper()} ({len(rows)}) ==")
        for r in rows[: args.limit]:
            print(f"  {r['slot_id']:18} {r['geo']:6} posts={r['posts']:<4} views={r['views']:<8} "
                  f"clicks={r['clicks']:<6} rev=${r['revenue_usd']:.2f}")
    return 0


def cmd_report_geo(args) -> int:
    rows = geo_accuracy_report(_store(), days=args.days)
    print(f"{'slot':18} {'geo':6} {'platform':10} {'views':>8} {'target %':>9}")
    for r in rows[: args.limit]:
        share = f"{r['target_geo_share']:.0f}" if r["target_geo_share"] is not None else "—"
        print(f"{r['slot_id']:18} {r['geo']:6} {r['platform']:10} {r['views']:>8} {share:>9}")
    return 0


def cmd_status(args) -> int:
    st = _store()
    conn = st._conn
    def one(q, *a):
        return conn.execute(q, a).fetchone()[0]
    print("слотов:      ", one("SELECT COUNT(*) FROM slots WHERE active=1"))
    print("аккаунтов:   ", one("SELECT COUNT(*) FROM accounts"))
    for s in ("planned", "rendered", "queued", "published", "failed", "skipped"):
        print(f"планов {s:10}", one("SELECT COUNT(*) FROM plans WHERE state=?", s))
    print("постов:      ", one("SELECT COUNT(*) FROM posts WHERE state='published'"))
    print("просмотров:  ", one("SELECT COALESCE(SUM(views),0) FROM metrics"))
    print("выручка $:   ", round(one("SELECT COALESCE(SUM(value_usd),0) FROM conversions"), 2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="traffic-engine", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor", help="проверить окружение и данные").set_defaults(fn=cmd_doctor)

    g = sub.add_parser("init-grid", help="создать слоты каналов из data/channels.json")
    g.add_argument("--all-geos", action="store_true", help="включая гео с priority > 3")
    g.set_defaults(fn=cmd_init_grid)

    s = sub.add_parser("slots", help="список слотов")
    s.add_argument("--geo"); s.add_argument("--platform")
    s.set_defaults(fn=cmd_slots)

    a = sub.add_parser("account", help="аккаунты")
    asub = a.add_subparsers(dest="acmd", required=True)
    aa = asub.add_parser("add")
    aa.add_argument("account_id"); aa.add_argument("--slot", required=True)
    aa.add_argument("--platform", required=True); aa.add_argument("--username", required=True)
    aa.add_argument("--cred"); aa.add_argument("--proxy"); aa.add_argument("--device")
    aa.add_argument("--state", default="warming"); aa.add_argument("--cap", type=int, default=1)
    aa.set_defaults(fn=cmd_account_add)
    ast_ = asub.add_parser("state")
    ast_.add_argument("account_id"); ast_.add_argument("state"); ast_.add_argument("--note")
    ast_.set_defaults(fn=cmd_account_state)

    ass = sub.add_parser("assets"); assub = ass.add_subparsers(dest="ascmd", required=True)
    asc = assub.add_parser("scan"); asc.add_argument("--dir"); asc.set_defaults(fn=cmd_assets_scan)

    pl = sub.add_parser("plan", help="построить план публикаций")
    pl.add_argument("--days", type=int, default=7); pl.add_argument("--geo")
    pl.set_defaults(fn=cmd_plan)

    rn = sub.add_parser("render", help="отрендерить запланированное")
    rn.add_argument("--limit", type=int, default=20); rn.add_argument("--horizon", type=int, default=2)
    rn.set_defaults(fn=cmd_render)

    pb = sub.add_parser("publish", help="опубликовать/подготовить киты")
    pb.add_argument("--limit", type=int, default=50); pb.add_argument("--until")
    pb.add_argument("--public-url", help="публичный URL рендера (нужен Instagram)")
    pb.set_defaults(fn=cmd_publish)

    rp = sub.add_parser("record-post", help="зафиксировать ручную публикацию")
    rp.add_argument("plan_id"); rp.add_argument("--account-id", required=True)
    rp.add_argument("--platform", required=True); rp.add_argument("--url")
    rp.add_argument("--remote-id"); rp.add_argument("--at")
    rp.set_defaults(fn=cmd_record_post)

    im = sub.add_parser("import-metrics"); im.add_argument("path"); im.set_defaults(fn=cmd_import_metrics)

    rv = sub.add_parser("review", help="что масштабировать, что закрывать")
    rv.add_argument("--days", type=int, default=14); rv.add_argument("--limit", type=int, default=30)
    rv.set_defaults(fn=cmd_review)

    rg = sub.add_parser("report-geo", help="доля просмотров из целевого гео")
    rg.add_argument("--days", type=int, default=14); rg.add_argument("--limit", type=int, default=40)
    rg.set_defaults(fn=cmd_report_geo)

    sub.add_parser("status", help="сводка").set_defaults(fn=cmd_status)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
