"""Фабрика публикаторов: режим берётся из слота, ключи — из окружения."""
from __future__ import annotations

import os

from ..models import Account, Platform, PublishMode
from .base import PublishContext, Publisher
from .instagram import InstagramPublisher
from .kit import KitPublisher
from .relay import RelayPublisher
from .tiktok import TikTokPublisher
from .youtube import YouTubePublisher

__all__ = ["get_publisher", "PublishContext", "Publisher"]


def get_publisher(platform: Platform, mode: PublishMode, account: Account) -> Publisher:
    if mode == PublishMode.KIT:
        return KitPublisher()
    if mode == PublishMode.RELAY:
        return RelayPublisher()

    ref = account.credential_ref or account.account_id.upper().replace("-", "_")
    token = os.getenv(f"{ref}_TOKEN", "")
    if not token:
        return KitPublisher()      # нет токена — деградируем в KIT, а не падаем

    if platform == Platform.YOUTUBE:
        return YouTubePublisher(token)
    if platform == Platform.TIKTOK:
        return TikTokPublisher(token, os.getenv(f"{ref}_PRIVACY", "PUBLIC_TO_EVERYONE"))
    if platform == Platform.INSTAGRAM:
        ig_id = os.getenv(f"{ref}_IG_USER_ID", "")
        if not ig_id:
            return KitPublisher()
        return InstagramPublisher(token, ig_id)
    return KitPublisher()
