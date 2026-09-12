"""YouTube Shorts через YouTube Data API v3 (videos.insert, resumable upload).

Ограничение, которое определяет архитектуру: квота считается НА ПРОЕКТ Google Cloud,
а не на канал. Стоимость videos.insert и дневной лимит квоты берутся из
data/platform_limits.json (поле units_per_upload / daily_quota_units) — там же
лежит ссылка на источник. Если каналов больше, чем позволяет квота, вариантов два:
запросить увеличение квоты у Google или часть каналов вести в режиме KIT/RELAY.

Shorts определяется вертикальным соотношением и длиной <= 3 минут; отдельного
«Shorts API» нет — грузится обычное видео.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests

from ..config import settings
from ..models import JobState, PostResult
from .base import PublishContext, Publisher, PublishMode

UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubePublisher(Publisher):
    mode = PublishMode.API

    def __init__(self, access_token: str):
        self.token = access_token

    def publish(self, ctx: PublishContext) -> PostResult:
        plan, rr = ctx.plan, ctx.render
        body = {
            "snippet": {
                "title": plan.title[:100],
                "description": self._description(ctx),
                "tags": [h.lstrip("#") for h in plan.hashtags][:15],
                "categoryId": "20",                       # Gaming
                "defaultLanguage": None,
                "defaultAudioLanguage": None,
            },
            "status": {
                "privacyStatus": "public",
                "selfDeclaredMadeForKids": False,
            },
        }
        body["snippet"] = {k: v for k, v in body["snippet"].items() if v is not None}
        if ctx.dry_run:
            return self._ok(ctx, remote_id="dry-run", url=None)

        path = Path(rr.video_path)
        size = path.stat().st_size
        init = requests.post(
            UPLOAD_URL,
            params={"uploadType": "resumable", "part": "snippet,status"},
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json; charset=UTF-8",
                "X-Upload-Content-Length": str(size),
                "X-Upload-Content-Type": "video/mp4",
            },
            data=json.dumps(body),
            timeout=60,
        )
        if init.status_code >= 400:
            return self._fail(ctx, f"init {init.status_code}: {init.text}",
                              state=self._state_for(init.status_code, init.text))
        session_url = init.headers.get("Location")
        if not session_url:
            return self._fail(ctx, "нет Location в ответе на init")

        with path.open("rb") as fh:
            up = requests.put(
                session_url,
                headers={"Content-Length": str(size), "Content-Type": "video/mp4"},
                data=fh,
                timeout=(60, 1800),
            )
        if up.status_code >= 400:
            return self._fail(ctx, f"upload {up.status_code}: {up.text}",
                              state=self._state_for(up.status_code, up.text))
        vid = up.json().get("id")
        return self._ok(ctx, vid, f"https://youtube.com/shorts/{vid}" if vid else None)

    def _description(self, ctx: PublishContext) -> str:
        plan = ctx.plan
        tags = " ".join("#" + h.lstrip("#") for h in plan.hashtags)
        link = ctx.plan.cta_text
        return f"{plan.caption}\n\n{link}\n\n{tags}".strip()[:4900]

    @staticmethod
    def _state_for(code: int, text: str) -> JobState:
        if code == 403 and "quota" in text.lower():
            return JobState.BLOCKED
        if code in (401, 403):
            return JobState.NEEDS_HUMAN
        return JobState.FAILED
