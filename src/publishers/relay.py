"""Режим RELAY: публикация через сторонний планировщик с мульти-аккаунтом.

Смысл: планировщик держит официальные интеграции и лимиты у себя, система отдаёт
ему готовый рендер + подпись + время. Конкретный провайдер и его эндпоинт задаются
в .env (RELAY_PROVIDER, RELAY_API_KEY) и в data/platform_limits.json -> relay.
Список провайдеров и их реальные лимиты/цены заполняются из ресерча.
"""
from __future__ import annotations

import requests

from ..config import platform_limits, settings
from ..models import JobState, PostResult, utcnow
from .base import PublishContext, Publisher, PublishMode


class RelayPublisher(Publisher):
    mode = PublishMode.RELAY

    def __init__(self, provider: str | None = None, api_key: str | None = None):
        cfg = settings()
        self.provider = provider or cfg.relay_provider
        self.api_key = api_key or cfg.relay_api_key
        self.conf = platform_limits().get("relay", {}).get(self.provider, {})

    def publish(self, ctx: PublishContext) -> PostResult:
        endpoint = self.conf.get("schedule_endpoint")
        if not endpoint:
            return self._fail(
                ctx,
                f"провайдер '{self.provider}' не описан в data/platform_limits.json -> relay",
                JobState.NEEDS_HUMAN,
            )
        if ctx.dry_run:
            return self._ok(ctx, "dry-run", None)
        payload = {
            "account": ctx.account.username,
            "platform": ctx.plan.platform.value,
            "publish_at": ctx.plan.scheduled_for_utc,
            "caption": ctx.plan.caption,
            "hashtags": ctx.plan.hashtags,
            "video_url": ctx.public_video_url,
        }
        r = requests.post(endpoint, headers={"Authorization": f"Bearer {self.api_key}"},
                          json=payload, timeout=120)
        if r.status_code >= 400:
            return self._fail(ctx, f"relay {r.status_code}: {r.text}")
        return self._ok(ctx, str(r.json().get("id", "")), None)
