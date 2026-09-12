"""Режим KIT: система не публикует сама, а готовит всё до кнопки «опубликовать».

Это основной режим для сетки из десятков аккаунтов: официальные API таких объёмов
не дают, а неофициальная автоматизация = потеря аккаунтов. Кит содержит файл,
подпись, хештеги, время и чеклист; факт публикации потом фиксируется вручную
командой `record-post`, чтобы метрики и атрибуция не разъезжались.
"""
from __future__ import annotations

from ..models import JobState, PostResult, utcnow
from ..render import write_post_kit
from .base import PublishContext, Publisher, PublishMode


class KitPublisher(Publisher):
    mode = PublishMode.KIT

    def publish(self, ctx: PublishContext) -> PostResult:
        path = write_post_kit(ctx.plan, ctx.render, ctx.account.username)
        return PostResult(
            plan_id=ctx.plan.plan_id, account_id=ctx.account.account_id,
            platform=ctx.plan.platform, state=JobState.QUEUED,
            remote_id=None, remote_url=str(path), published_at=None, mode=self.mode,
        )
