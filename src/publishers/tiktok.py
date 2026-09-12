"""TikTok через Content Posting API v2.

Важные ограничения (проверяются ресерчем, значения — в data/platform_limits.json):
* приложение проходит аудит; до аудита посты уходят только с privacy_level,
  ограниченным самим автором (SELF_ONLY) — то есть публичного залива нет;
* каждый аккаунт должен сам выдать доступ приложению через OAuth;
* режим PULL_FROM_URL требует верифицированного домена, FILE_UPLOAD грузит байты чанками.

Если аудит не пройден или аккаунтов много — эти слоты работают в режиме KIT.
"""
from __future__ import annotations

from pathlib import Path

import requests

from ..models import JobState, PostResult
from .base import PublishContext, Publisher, PublishMode

INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"
STATUS = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
CHUNK = 10 * 1024 * 1024


class TikTokPublisher(Publisher):
    mode = PublishMode.API

    def __init__(self, access_token: str, privacy_level: str = "PUBLIC_TO_EVERYONE"):
        self.token = access_token
        self.privacy_level = privacy_level

    def publish(self, ctx: PublishContext) -> PostResult:
        plan, rr = ctx.plan, ctx.render
        caption = f"{plan.caption} {' '.join('#' + h.lstrip('#') for h in plan.hashtags)}".strip()
        if ctx.dry_run:
            return self._ok(ctx, "dry-run", None)

        path = Path(rr.video_path)
        size = path.stat().st_size
        chunk = min(CHUNK, size)
        total_chunks = max(1, -(-size // chunk))
        payload = {
            "post_info": {
                "title": caption[:2200],
                "privacy_level": self.privacy_level,
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": size,
                "chunk_size": chunk,
                "total_chunk_count": total_chunks,
            },
        }
        r = requests.post(
            INIT,
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json; charset=UTF-8"},
            json=payload, timeout=60,
        )
        if r.status_code >= 400:
            return self._fail(ctx, f"init {r.status_code}: {r.text}", self._state_for(r.status_code, r.text))
        data = (r.json() or {}).get("data", {})
        publish_id, upload_url = data.get("publish_id"), data.get("upload_url")
        if not upload_url:
            return self._fail(ctx, f"нет upload_url: {r.text[:500]}")

        with path.open("rb") as fh:
            for idx in range(total_chunks):
                start = idx * chunk
                blob = fh.read(chunk)
                end = start + len(blob) - 1
                up = requests.put(
                    upload_url,
                    headers={"Content-Range": f"bytes {start}-{end}/{size}",
                             "Content-Type": "video/mp4",
                             "Content-Length": str(len(blob))},
                    data=blob, timeout=(60, 1800),
                )
                if up.status_code >= 400:
                    return self._fail(ctx, f"chunk {idx} {up.status_code}: {up.text}")

        return self._ok(ctx, publish_id, None)

    def check_status(self, publish_id: str) -> dict:
        r = requests.post(
            STATUS,
            headers={"Authorization": f"Bearer {self.token}",
                     "Content-Type": "application/json; charset=UTF-8"},
            json={"publish_id": publish_id}, timeout=30,
        )
        return r.json() if r.status_code < 400 else {"error": r.text}

    @staticmethod
    def _state_for(code: int, text: str) -> JobState:
        low = text.lower()
        if "spam_risk" in low or "rate" in low:
            return JobState.BLOCKED
        if code in (401, 403):
            return JobState.NEEDS_HUMAN
        return JobState.FAILED
