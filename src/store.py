"""Состояние системы в SQLite. Без ORM — один файл, явные запросы.

Зачем состояние: без него нельзя (а) не запостить одно и то же дважды,
(б) соблюдать дневные лимиты аккаунтов, (в) считать, какой канал/гео даёт деньги.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable

from .models import (
    Account, ChannelSlot, JobState, MetricSnapshot, Platform,
    PostResult, PublishMode, RenderResult, VideoPlan, utcnow,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS slots (
    slot_id TEXT PRIMARY KEY, geo TEXT, platform TEXT, theme TEXT,
    target_game TEXT, handle TEXT, bio TEXT, persona TEXT,
    posts_per_day INTEGER, publish_mode TEXT, attribution_token TEXT,
    content_formats TEXT, active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY, slot_id TEXT, platform TEXT, username TEXT,
    created_at TEXT, credential_ref TEXT, proxy_ref TEXT, device_ref TEXT,
    state TEXT, daily_cap INTEGER, notes TEXT
);
CREATE TABLE IF NOT EXISTS plans (
    plan_id TEXT PRIMARY KEY, slot_id TEXT, geo TEXT, platform TEXT,
    format_id TEXT, hook_text TEXT, caption TEXT, title TEXT,
    hashtags TEXT, asset_ids TEXT, audio_asset_id TEXT, variant_seed INTEGER,
    target_duration_s REAL, scheduled_for_utc TEXT, state TEXT,
    body_beats TEXT, cta_text TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS renders (
    plan_id TEXT PRIMARY KEY, video_path TEXT, thumb_path TEXT, duration_s REAL,
    width INTEGER, height INTEGER, checksum TEXT, rendered_at TEXT
);
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT, account_id TEXT, platform TEXT, state TEXT,
    remote_id TEXT, remote_url TEXT, error TEXT, published_at TEXT, mode TEXT,
    UNIQUE(plan_id, account_id)
);
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id TEXT, account_id TEXT, platform TEXT, captured_at TEXT,
    views INTEGER, likes INTEGER, comments INTEGER, shares INTEGER, saves INTEGER,
    avg_watch_s REAL, completion_rate REAL, profile_views INTEGER, link_clicks INTEGER,
    geo_breakdown TEXT
);
CREATE TABLE IF NOT EXISTS conversions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    attribution_token TEXT, kind TEXT, value_usd REAL, geo TEXT,
    happened_at TEXT, external_ref TEXT
);
CREATE TABLE IF NOT EXISTS asset_usage (
    asset_id TEXT, slot_id TEXT, used_at TEXT
);
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    at TEXT, level TEXT, source TEXT, message TEXT, payload TEXT
);
CREATE INDEX IF NOT EXISTS idx_posts_account ON posts(account_id, published_at);
CREATE INDEX IF NOT EXISTS idx_metrics_plan ON metrics(plan_id, captured_at);
CREATE INDEX IF NOT EXISTS idx_plans_sched ON plans(scheduled_for_utc, state);
"""


class Store:
    def __init__(self, path: str | Path = "state.db"):
        self.path = str(path)
        self._conn = sqlite3.connect(self.path)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    @contextmanager
    def tx(self):
        try:
            yield self._conn
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    # ---------- slots / accounts ----------

    def upsert_slot(self, s: ChannelSlot) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO slots (slot_id, geo, platform, theme, target_game, handle, bio,
                       persona, posts_per_day, publish_mode, attribution_token, content_formats, active)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(slot_id) DO UPDATE SET
                       geo=excluded.geo, platform=excluded.platform, theme=excluded.theme,
                       target_game=excluded.target_game, handle=excluded.handle, bio=excluded.bio,
                       persona=excluded.persona, posts_per_day=excluded.posts_per_day,
                       publish_mode=excluded.publish_mode, attribution_token=excluded.attribution_token,
                       content_formats=excluded.content_formats, active=excluded.active""",
                (s.slot_id, s.geo, s.platform.value, s.theme, s.target_game, s.handle, s.bio,
                 s.persona, s.posts_per_day, s.publish_mode.value, s.attribution_token,
                 json.dumps(s.content_formats, ensure_ascii=False), int(s.active)),
            )

    def slots(self, geo: str | None = None, platform: Platform | None = None,
              active_only: bool = True) -> list[ChannelSlot]:
        q = "SELECT * FROM slots WHERE 1=1"
        args: list[Any] = []
        if geo:
            q += " AND geo = ?"
            args.append(geo)
        if platform:
            q += " AND platform = ?"
            args.append(platform.value)
        if active_only:
            q += " AND active = 1"
        rows = self._conn.execute(q, args).fetchall()
        return [
            ChannelSlot(
                slot_id=r["slot_id"], geo=r["geo"], platform=Platform(r["platform"]),
                theme=r["theme"], target_game=r["target_game"],
                content_formats=json.loads(r["content_formats"] or "[]"),
                handle=r["handle"], bio=r["bio"], persona=r["persona"] or "faceless",
                posts_per_day=r["posts_per_day"] or 1,
                publish_mode=PublishMode(r["publish_mode"] or "kit"),
                attribution_token=r["attribution_token"], active=bool(r["active"]),
            )
            for r in rows
        ]

    def upsert_account(self, a: Account) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO accounts (account_id, slot_id, platform, username, created_at,
                       credential_ref, proxy_ref, device_ref, state, daily_cap, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(account_id) DO UPDATE SET
                       slot_id=excluded.slot_id, username=excluded.username,
                       credential_ref=excluded.credential_ref, proxy_ref=excluded.proxy_ref,
                       device_ref=excluded.device_ref, state=excluded.state,
                       daily_cap=excluded.daily_cap, notes=excluded.notes""",
                (a.account_id, a.slot_id, a.platform.value, a.username, a.created_at,
                 a.credential_ref, a.proxy_ref, a.device_ref, a.state, a.daily_cap, a.notes),
            )

    def account_for_slot(self, slot_id: str) -> Account | None:
        r = self._conn.execute(
            "SELECT * FROM accounts WHERE slot_id = ? AND state IN ('active','warming') LIMIT 1",
            (slot_id,),
        ).fetchone()
        if not r:
            return None
        return Account(
            account_id=r["account_id"], slot_id=r["slot_id"], platform=Platform(r["platform"]),
            username=r["username"], created_at=r["created_at"], credential_ref=r["credential_ref"],
            proxy_ref=r["proxy_ref"], device_ref=r["device_ref"], state=r["state"],
            daily_cap=r["daily_cap"] or 1, notes=r["notes"] or "",
        )

    def set_account_state(self, account_id: str, state: str, note: str = "") -> None:
        with self.tx() as c:
            c.execute("UPDATE accounts SET state = ?, notes = COALESCE(notes,'') || ? WHERE account_id = ?",
                      (state, f" | {utcnow()}: {note}" if note else "", account_id))

    def posts_today(self, account_id: str, day_utc: str) -> int:
        r = self._conn.execute(
            "SELECT COUNT(*) AS n FROM posts WHERE account_id = ? AND state = 'published' "
            "AND substr(published_at,1,10) = ?",
            (account_id, day_utc),
        ).fetchone()
        return int(r["n"] or 0)

    # ---------- plans / renders / posts ----------

    def save_plan(self, p: VideoPlan) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO plans (plan_id, slot_id, geo, platform, format_id, hook_text,
                       caption, title, hashtags, asset_ids, audio_asset_id, variant_seed,
                       target_duration_s, scheduled_for_utc, state, body_beats, cta_text, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(plan_id) DO UPDATE SET
                       state=excluded.state, scheduled_for_utc=excluded.scheduled_for_utc,
                       caption=excluded.caption, title=excluded.title""",
                (p.plan_id, p.slot_id, p.geo, p.platform.value, p.format_id, p.hook_text,
                 p.caption, p.title, json.dumps(p.hashtags, ensure_ascii=False),
                 json.dumps(p.asset_ids), p.audio_asset_id, p.variant_seed,
                 p.target_duration_s, p.scheduled_for_utc, p.state.value,
                 json.dumps(p.body_beats, ensure_ascii=False), p.cta_text, utcnow()),
            )

    def plans_due(self, until_utc: str, state: JobState = JobState.RENDERED) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM plans WHERE state = ? AND scheduled_for_utc <= ? ORDER BY scheduled_for_utc",
            (state.value, until_utc),
        ).fetchall()
        return [dict(r) for r in rows]

    def set_plan_state(self, plan_id: str, state: JobState) -> None:
        with self.tx() as c:
            c.execute("UPDATE plans SET state = ? WHERE plan_id = ?", (state.value, plan_id))

    def save_render(self, r: RenderResult) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO renders (plan_id, video_path, thumb_path, duration_s, width, height,
                       checksum, rendered_at) VALUES (?,?,?,?,?,?,?,?)
                   ON CONFLICT(plan_id) DO UPDATE SET video_path=excluded.video_path,
                       checksum=excluded.checksum, rendered_at=excluded.rendered_at""",
                (r.plan_id, r.video_path, r.thumb_path, r.duration_s, r.width, r.height,
                 r.checksum, r.rendered_at),
            )

    def render_for(self, plan_id: str) -> dict | None:
        r = self._conn.execute("SELECT * FROM renders WHERE plan_id = ?", (plan_id,)).fetchone()
        return dict(r) if r else None

    def checksum_seen(self, checksum: str) -> bool:
        """Защита от публикации побайтово одинакового файла в разные аккаунты."""
        r = self._conn.execute("SELECT 1 FROM renders WHERE checksum = ? LIMIT 1", (checksum,)).fetchone()
        return r is not None

    def save_post(self, res: PostResult) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO posts (plan_id, account_id, platform, state, remote_id, remote_url,
                       error, published_at, mode) VALUES (?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(plan_id, account_id) DO UPDATE SET
                       state=excluded.state, remote_id=excluded.remote_id,
                       remote_url=excluded.remote_url, error=excluded.error,
                       published_at=excluded.published_at, mode=excluded.mode""",
                (res.plan_id, res.account_id, res.platform.value, res.state.value, res.remote_id,
                 res.remote_url, res.error, res.published_at, res.mode.value),
            )

    def published_posts(self, since_utc: str | None = None) -> list[dict]:
        q = "SELECT * FROM posts WHERE state = 'published'"
        args: list[Any] = []
        if since_utc:
            q += " AND published_at >= ?"
            args.append(since_utc)
        return [dict(r) for r in self._conn.execute(q, args).fetchall()]

    # ---------- metrics / conversions ----------

    def save_metric(self, m: MetricSnapshot) -> None:
        with self.tx() as c:
            c.execute(
                """INSERT INTO metrics (plan_id, account_id, platform, captured_at, views, likes,
                       comments, shares, saves, avg_watch_s, completion_rate, profile_views,
                       link_clicks, geo_breakdown) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (m.plan_id, m.account_id, m.platform.value, m.captured_at, m.views, m.likes,
                 m.comments, m.shares, m.saves, m.avg_watch_s, m.completion_rate,
                 m.profile_views, m.link_clicks, json.dumps(m.geo_breakdown)),
            )

    def latest_metrics(self, plan_id: str) -> dict | None:
        r = self._conn.execute(
            "SELECT * FROM metrics WHERE plan_id = ? ORDER BY captured_at DESC LIMIT 1", (plan_id,)
        ).fetchone()
        return dict(r) if r else None

    def record_conversion(self, attribution_token: str, kind: str, value_usd: float,
                          geo: str = "", external_ref: str = "") -> None:
        with self.tx() as c:
            c.execute(
                "INSERT INTO conversions (attribution_token, kind, value_usd, geo, happened_at, external_ref)"
                " VALUES (?,?,?,?,?,?)",
                (attribution_token, kind, value_usd, geo, utcnow(), external_ref),
            )

    def slot_performance(self, days: int = 14) -> list[dict]:
        """Сводка по слотам: просмотры, клики, деньги. Основа решений planner-а."""
        rows = self._conn.execute(
            """
            SELECT s.slot_id, s.geo, s.platform, s.theme, s.attribution_token,
                   COUNT(DISTINCT p.plan_id) AS posts,
                   COALESCE(SUM(mx.views), 0) AS views,
                   COALESCE(SUM(mx.link_clicks), 0) AS clicks,
                   (SELECT COALESCE(SUM(value_usd),0) FROM conversions cv
                      WHERE cv.attribution_token = s.attribution_token) AS revenue_usd
            FROM slots s
            LEFT JOIN plans p ON p.slot_id = s.slot_id
            LEFT JOIN (
                SELECT m1.* FROM metrics m1
                JOIN (SELECT plan_id, MAX(captured_at) AS mc FROM metrics GROUP BY plan_id) m2
                  ON m1.plan_id = m2.plan_id AND m1.captured_at = m2.mc
            ) mx ON mx.plan_id = p.plan_id
            GROUP BY s.slot_id
            ORDER BY views DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def log(self, level: str, source: str, message: str, payload: Any = None) -> None:
        with self.tx() as c:
            c.execute("INSERT INTO events (at, level, source, message, payload) VALUES (?,?,?,?,?)",
                      (utcnow(), level, source, message,
                       json.dumps(payload, ensure_ascii=False, default=str) if payload else None))

    def mark_asset_used(self, asset_ids: Iterable[str], slot_id: str) -> None:
        with self.tx() as c:
            c.executemany("INSERT INTO asset_usage (asset_id, slot_id, used_at) VALUES (?,?,?)",
                          [(a, slot_id, utcnow()) for a in asset_ids])

    def asset_used_by_slot(self, asset_id: str, slot_id: str) -> bool:
        r = self._conn.execute(
            "SELECT 1 FROM asset_usage WHERE asset_id = ? AND slot_id = ? LIMIT 1",
            (asset_id, slot_id),
        ).fetchone()
        return r is not None

    def close(self) -> None:
        self._conn.close()
