"""Сбор метрик и атрибуция выручки.

Без этого блока вся система — генератор видео в пустоту: решения «какое гео живое»,
«какой канал закрыть», «какой формат масштабировать» принимаются только здесь.

Три источника данных:
1. API площадок — там, где аккаунт подключён (points 1-3 ниже).
2. Ручной импорт CSV из нативной аналитики — для аккаунтов в режиме KIT.
3. Вебхуки платёжки/Discord — фактические деньги, привязанные к attribution_token.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import requests

from .models import MetricSnapshot, Platform, utcnow
from .store import Store


# ---------- 1. API площадок ----------

def fetch_youtube(store: Store, access_token: str, video_ids: list[str],
                  account_id: str) -> list[MetricSnapshot]:
    """videos.list?part=statistics — дешёво по квоте (1 единица за запрос до 50 id)."""
    out: list[MetricSnapshot] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "statistics", "id": ",".join(batch)},
            headers={"Authorization": f"Bearer {access_token}"}, timeout=60,
        )
        if r.status_code >= 400:
            store.log("error", "tracker.youtube", f"{r.status_code}: {r.text[:300]}")
            continue
        for item in r.json().get("items", []):
            st = item.get("statistics", {})
            out.append(MetricSnapshot(
                plan_id="", account_id=account_id, platform=Platform.YOUTUBE,
                captured_at=utcnow(),
                views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)),
                comments=int(st.get("commentCount", 0)),
            ))
    return out


def fetch_tiktok(store: Store, access_token: str, account_id: str) -> list[MetricSnapshot]:
    """/v2/video/list/ отдаёт метрики по своим видео (нужен scope video.list)."""
    r = requests.post(
        "https://open.tiktokapis.com/v2/video/list/",
        params={"fields": "id,title,view_count,like_count,comment_count,share_count"},
        headers={"Authorization": f"Bearer {access_token}",
                 "Content-Type": "application/json"},
        json={"max_count": 20}, timeout=60,
    )
    if r.status_code >= 400:
        store.log("error", "tracker.tiktok", f"{r.status_code}: {r.text[:300]}")
        return []
    out = []
    for v in (r.json().get("data", {}) or {}).get("videos", []):
        out.append(MetricSnapshot(
            plan_id="", account_id=account_id, platform=Platform.TIKTOK, captured_at=utcnow(),
            views=int(v.get("view_count", 0)), likes=int(v.get("like_count", 0)),
            comments=int(v.get("comment_count", 0)), shares=int(v.get("share_count", 0)),
        ))
    return out


def fetch_instagram(store: Store, access_token: str, media_ids: list[str],
                    account_id: str) -> list[MetricSnapshot]:
    """insights по рилсу: views/likes/comments/shares/saved — набор полей меняется,
    актуальный список держим в data/platform_limits.json -> instagram.insight_metrics."""
    out = []
    for mid in media_ids:
        r = requests.get(
            f"https://graph.facebook.com/v21.0/{mid}/insights",
            params={"metric": "views,likes,comments,shares,saved,reach",
                    "access_token": access_token}, timeout=45,
        )
        if r.status_code >= 400:
            store.log("error", "tracker.instagram", f"{mid}: {r.text[:200]}")
            continue
        vals = {d["name"]: (d.get("values") or [{}])[0].get("value", 0)
                for d in r.json().get("data", [])}
        out.append(MetricSnapshot(
            plan_id="", account_id=account_id, platform=Platform.INSTAGRAM, captured_at=utcnow(),
            views=int(vals.get("views", 0) or vals.get("reach", 0)),
            likes=int(vals.get("likes", 0)), comments=int(vals.get("comments", 0)),
            shares=int(vals.get("shares", 0)), saves=int(vals.get("saved", 0)),
        ))
    return out


# ---------- 2. Ручной импорт ----------

REQUIRED_CSV = {"plan_id", "views"}


def import_metrics_csv(store: Store, path: str | Path) -> int:
    """Импорт из нативной аналитики. Колонки: plan_id, account_id, platform, views,
    likes, comments, shares, saves, avg_watch_s, completion_rate, profile_views,
    link_clicks, geo_top (пример: US:62,IN:11)."""
    n = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if rows and not REQUIRED_CSV.issubset(rows[0].keys()):
        raise ValueError(f"в CSV нужны колонки минимум {REQUIRED_CSV}, есть: {list(rows[0])}")
    for r in rows:
        geo = {}
        for chunk in (r.get("geo_top") or "").split(","):
            if ":" in chunk:
                k, v = chunk.split(":", 1)
                try:
                    geo[k.strip().upper()] = float(v)
                except ValueError:
                    pass
        store.save_metric(MetricSnapshot(
            plan_id=r["plan_id"], account_id=r.get("account_id", ""),
            platform=Platform(r.get("platform", "tiktok")), captured_at=utcnow(),
            views=int(float(r.get("views") or 0)), likes=int(float(r.get("likes") or 0)),
            comments=int(float(r.get("comments") or 0)), shares=int(float(r.get("shares") or 0)),
            saves=int(float(r.get("saves") or 0)),
            avg_watch_s=float(r["avg_watch_s"]) if r.get("avg_watch_s") else None,
            completion_rate=float(r["completion_rate"]) if r.get("completion_rate") else None,
            profile_views=int(float(r["profile_views"])) if r.get("profile_views") else None,
            link_clicks=int(float(r["link_clicks"])) if r.get("link_clicks") else None,
            geo_breakdown=geo,
        ))
        n += 1
    store.log("info", "tracker", f"импортировано метрик: {n}")
    return n


# ---------- 3. Деньги ----------

def ingest_conversion(store: Store, payload: dict) -> None:
    """Приём вебхука от платёжки/Discord-бота.

    Ожидается, что в payload есть метка источника: `attribution_token` или поле,
    в котором она зашита (promo/coupon/invite/utm_content). Без метки конверсия
    попадает в бакет 'unattributed' — по нему видно, сколько трафика мы не считаем.
    """
    token = (
        payload.get("attribution_token")
        or payload.get("coupon")
        or payload.get("promo")
        or payload.get("invite")
        or (payload.get("utm") or {}).get("content")
        or "unattributed"
    )
    value = float(payload.get("value_usd") or payload.get("amount") or 0)
    store.record_conversion(
        attribution_token=str(token),
        kind=str(payload.get("kind") or payload.get("event") or "purchase"),
        value_usd=value,
        geo=str(payload.get("geo") or ""),
        external_ref=str(payload.get("id") or payload.get("order_id") or ""),
    )


def geo_accuracy_report(store: Store, days: int = 14) -> list[dict]:
    """Главный отчёт по гео: какая доля просмотров реально пришла из целевой страны.

    Если целевое гео стабильно ниже порога — проблема в контенте и языке, а не в прокси.
    """
    rows = []
    for slot in store.slots():
        views_total = 0
        target_share: list[float] = []
        for p in store.published_posts():
            if p["account_id"] and p["plan_id"].startswith(slot.slot_id):
                m = store.latest_metrics(p["plan_id"])
                if not m:
                    continue
                views_total += int(m["views"] or 0)
                geo = json.loads(m["geo_breakdown"] or "{}")
                if geo:
                    target_share.append(float(geo.get(slot.geo.upper(), 0)))
        if views_total:
            rows.append({
                "slot_id": slot.slot_id, "geo": slot.geo, "platform": slot.platform.value,
                "views": views_total,
                "target_geo_share": round(sum(target_share) / len(target_share), 1) if target_share else None,
            })
    return sorted(rows, key=lambda r: r["views"], reverse=True)
