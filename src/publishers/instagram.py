"""Instagram Reels через Graph API (media container -> media_publish).

Архитектурное следствие: Instagram НЕ принимает байты файла — он забирает видео
по публичной ссылке (video_url). Значит в системе обязателен шаг «выложить рендер
на публичный хостинг» (S3/R2/любой статик) перед публикацией. Лимит постов в сутки
и требования к аккаунту (professional) — в data/platform_limits.json.
"""
from __future__ import annotations

import time

import requests

from ..models import JobState, PostResult
from .base import PublishContext, Publisher, PublishMode

GRAPH = "https://graph.facebook.com/v21.0"


class InstagramPublisher(Publisher):
    mode = PublishMode.API

    def __init__(self, access_token: str, ig_user_id: str):
        self.token = access_token
        self.ig_user_id = ig_user_id

    def publish(self, ctx: PublishContext) -> PostResult:
        plan = ctx.plan
        if not ctx.public_video_url:
            return self._fail(
                ctx,
                "Instagram требует публичный video_url. Загрузи рендер на хостинг и передай "
                "public_video_url (см. SPEC.md, «Хостинг рендеров»).",
                JobState.NEEDS_HUMAN,
            )
        caption = f"{plan.caption}\n\n{plan.cta_text}\n{' '.join('#' + h.lstrip('#') for h in plan.hashtags)}"
        if ctx.dry_run:
            return self._ok(ctx, "dry-run", None)

        create = requests.post(
            f"{GRAPH}/{self.ig_user_id}/media",
            data={"media_type": "REELS", "video_url": ctx.public_video_url,
                  "caption": caption[:2200], "share_to_feed": "true",
                  "access_token": self.token},
            timeout=90,
        )
        if create.status_code >= 400:
            return self._fail(ctx, f"container {create.status_code}: {create.text}",
                              self._state_for(create.status_code, create.text))
        creation_id = create.json().get("id")

        # Instagram обрабатывает видео асинхронно: публиковать можно только после FINISHED
        for _ in range(30):
            st = requests.get(
                f"{GRAPH}/{creation_id}",
                params={"fields": "status_code,status", "access_token": self.token}, timeout=30,
            ).json()
            code = st.get("status_code")
            if code == "FINISHED":
                break
            if code == "ERROR":
                return self._fail(ctx, f"обработка не удалась: {st}")
            time.sleep(10)
        else:
            return self._fail(ctx, "контейнер не дошёл до FINISHED за 5 минут", JobState.NEEDS_HUMAN)

        pub = requests.post(
            f"{GRAPH}/{self.ig_user_id}/media_publish",
            data={"creation_id": creation_id, "access_token": self.token}, timeout=60,
        )
        if pub.status_code >= 400:
            return self._fail(ctx, f"publish {pub.status_code}: {pub.text}",
                              self._state_for(pub.status_code, pub.text))
        mid = pub.json().get("id")
        return self._ok(ctx, mid, None)

    @staticmethod
    def _state_for(code: int, text: str) -> JobState:
        low = text.lower()
        if "limit" in low or "rate" in low:
            return JobState.BLOCKED
        if code in (401, 403) or "token" in low:
            return JobState.NEEDS_HUMAN
        return JobState.FAILED
