"""Общий интерфейс публикации.

Три режима (см. SPEC.md «Модель публикации»):
  API   — официальное API площадки, нужен OAuth-токен конкретного аккаунта;
  RELAY — сторонний планировщик с мульти-аккаунтом (он держит интеграции);
  KIT   — система готовит файл + тексты + время, публикует человек/устройство.

Почему так, а не «скрипт сам постит в 400 аккаунтов»: официальные API дают
публикацию только от аккаунтов, которые сами выдали доступ приложению, и на
каждое приложение есть аудит и квоты. Всё остальное — автоматизация в обход
правил площадки: она работает до первой волны блокировок и утаскивает за собой
аккаунты целиком. Поэтому масштаб делается числом аккаунтов в KIT/RELAY, а не
попыткой обмануть API.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass

from ..models import Account, JobState, PostResult, PublishMode, RenderResult, VideoPlan, utcnow


@dataclass
class PublishContext:
    plan: VideoPlan
    render: RenderResult
    account: Account
    dry_run: bool = True
    public_video_url: str | None = None   # нужен площадкам, которые тянут файл по ссылке


class Publisher(abc.ABC):
    mode: PublishMode

    @abc.abstractmethod
    def publish(self, ctx: PublishContext) -> PostResult:
        ...

    def _ok(self, ctx: PublishContext, remote_id: str | None, url: str | None) -> PostResult:
        return PostResult(
            plan_id=ctx.plan.plan_id, account_id=ctx.account.account_id,
            platform=ctx.plan.platform, state=JobState.PUBLISHED,
            remote_id=remote_id, remote_url=url, published_at=utcnow(), mode=self.mode,
        )

    def _fail(self, ctx: PublishContext, err: str, state: JobState = JobState.FAILED) -> PostResult:
        return PostResult(
            plan_id=ctx.plan.plan_id, account_id=ctx.account.account_id,
            platform=ctx.plan.platform, state=state, error=err[:2000], mode=self.mode,
        )
