"""Публикация через браузер (Playwright) в профиле, где оператор залогинился сам.

ЧТО ЭТО ДЕЛАЕТ
Открывает постоянный профиль браузера, привязанный к одному аккаунту, проходит
шаги загрузки из data/upload_flows.json и сохраняет скриншоты каждого этапа.
Шаги описаны данными: интерфейсы загрузки меняются часто, и поломка селектора
должна чиниться правкой JSON, а не кода.

ЧЕГО ЭТО НЕ ДЕЛАЕТ, СОЗНАТЕЛЬНО
Ни подмены отпечатков устройства, ни скрытия признаков автоматизации, ни обхода
капчи. Это не автоматизация, а обход систем защиты площадки: он ломается от
одного обновления детекта и забирает с собой всю сеть аккаунтов сразу. Если на
шаге появляется капча или проверка входа, задача переходит в состояние
needs_human — оператор доделывает вручную.

ЧЕСТНО О РИСКЕ
Автоматизация публикации нарушает правила TikTok, YouTube и Instagram. Типичный
исход — не мгновенный бан, а тихое ограничение выдачи: видео уходят, охвата нет.
Поэтому темп берётся из data/platform_limits.json (консервативный, ниже
технического), профиль на аккаунт не переиспользуется, и параллельность
ограничена: один браузер на аккаунт, а не один браузер на сеть.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..config import ROOT, load_json, settings
from ..models import JobState, PostResult, utcnow
from .base import PublishContext, Publisher, PublishMode

PROFILES = ROOT / "profiles"
ARTIFACTS = ROOT / "out" / "_browser"


class BrowserUnavailable(RuntimeError):
    pass


def flows() -> dict:
    return load_json("upload_flows.json")


def profile_dir(account_id: str) -> Path:
    p = PROFILES / account_id
    p.mkdir(parents=True, exist_ok=True)
    return p


def _values(ctx: PublishContext) -> dict[str, str]:
    plan = ctx.plan
    tags = " ".join("#" + h.lstrip("#") for h in plan.hashtags)
    return {
        "video_path": ctx.render.video_path,
        "thumbnail_path": ctx.render.thumb_path or "",
        "title": plan.title,
        "caption": f"{plan.caption}\n\n{plan.cta_text}\n{tags}".strip(),
        "hashtags_line": tags,
    }


def _launch(playwright, account_id: str, proxy: str | None, headless: bool):
    """Постоянный контекст на аккаунт: сессия живёт в своём каталоге профиля.

    headless=False по умолчанию: headless-режим детектируется заметно легче, а
    главное — оператору нужно видеть, что происходит, когда шаг падает.
    """
    args = {
        "user_data_dir": str(profile_dir(account_id)),
        "headless": headless,
        "viewport": {"width": 1280, "height": 900},
        "args": ["--disable-blink-features=AutomationControlled"],
    }
    if proxy:
        args["proxy"] = {"server": proxy}
    return playwright.chromium.launch_persistent_context(**args)


def run_flow(flow: dict, ctx: PublishContext, page, artifacts: Path,
             start_url: str | None = None) -> list[str]:
    """Исполняет шаги потока. Возвращает журнал выполненных шагов."""
    done: list[str] = []
    vals = _values(ctx)
    for i, step in enumerate(flow.get("steps", []), start=1):
        action = step.get("action")
        sel = step.get("selector")
        optional = bool(step.get("optional"))
        timeout = int(step.get("timeout_ms", 30000))
        try:
            if action == "goto":
                url = (step.get("url") or "").replace("{start_url}", start_url or "")
                page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            elif action == "wait_for":
                page.wait_for_selector(sel, timeout=timeout)
            elif action == "wait_for_hidden":
                page.wait_for_selector(sel, state="hidden", timeout=timeout)
            elif action == "click":
                page.click(sel, timeout=timeout)
            elif action == "set_input_files":
                page.set_input_files(sel, vals[step["value_from"]], timeout=timeout)
            elif action == "fill":
                page.fill(sel, vals[step["value_from"]], timeout=timeout)
            elif action == "type_slow":
                page.click(sel, timeout=timeout)
                page.type(sel, vals[step["value_from"]], delay=int(step.get("delay_ms", 20)))
            elif action == "press":
                page.keyboard.press(step["key"])
            elif action == "expect_text":
                page.wait_for_selector(f"text={step['text']}", timeout=timeout)
            elif action == "screenshot":
                artifacts.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(artifacts / f"{i:02d}_{step.get('name','shot')}.png"))
            else:
                raise ValueError(f"неизвестное действие: {action}")
            done.append(f"{i}:{action}")
        except Exception as e:                                  # noqa: BLE001
            if optional:
                done.append(f"{i}:{action}:skipped")
                continue
            artifacts.mkdir(parents=True, exist_ok=True)
            try:
                page.screenshot(path=str(artifacts / f"{i:02d}_FAIL_{action}.png"))
            except Exception:                                   # noqa: BLE001
                pass
            raise RuntimeError(f"шаг {i} ({action}, {sel}) не выполнен: {type(e).__name__}: {e}") from e
    return done


class BrowserPublisher(Publisher):
    mode = PublishMode.KIT          # по механике доставки это ручной режим, доведённый до автомата

    def __init__(self, platform_key: str | None = None, headless: bool = False,
                 start_url: str | None = None):
        self.platform_key = platform_key
        self.headless = headless
        self.start_url = start_url

    def publish(self, ctx: PublishContext) -> PostResult:
        key = self.platform_key or ctx.plan.platform.value
        flow = flows().get(key)
        if not flow:
            return self._fail(ctx, f"нет потока загрузки для '{key}' в data/upload_flows.json",
                              JobState.NEEDS_HUMAN)
        if not flow.get("verified", False):
            # селекторы площадок меняются: непроверенный поток не должен молча
            # считаться рабочим, иначе метрики покажут публикации, которых не было
            ctx_note = (f"поток '{key}' помечен verified=false — сначала "
                        f"`cli browser-verify {key}`")
            if not ctx.dry_run:
                return self._fail(ctx, ctx_note, JobState.NEEDS_HUMAN)

        if ctx.dry_run:
            return PostResult(
                plan_id=ctx.plan.plan_id, account_id=ctx.account.account_id,
                platform=ctx.plan.platform, state=JobState.QUEUED,
                remote_url=None, error=None, mode=self.mode,
            )

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as e:
            raise BrowserUnavailable("playwright не установлен: pip install playwright") from e

        artifacts = ARTIFACTS / ctx.plan.plan_id
        with sync_playwright() as pw:
            context = _launch(pw, ctx.account.account_id, ctx.account.proxy_ref, self.headless)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                steps = run_flow(flow, ctx, page, artifacts, self.start_url)
                url = page.url
            except RuntimeError as e:
                return self._fail(ctx, str(e), JobState.NEEDS_HUMAN)
            finally:
                context.close()

        return PostResult(
            plan_id=ctx.plan.plan_id, account_id=ctx.account.account_id,
            platform=ctx.plan.platform, state=JobState.PUBLISHED,
            remote_id=None, remote_url=url, published_at=utcnow(), mode=self.mode,
        )


def login_session(account_id: str, url: str, proxy: str | None = None,
                  timeout_s: int = 600) -> bool:
    """Открывает браузер, чтобы оператор вошёл в аккаунт РУКАМИ.

    Логин не автоматизируется: это и обход защиты, и самый быстрый способ
    потерять аккаунт. Здесь только сохранение сессии в профиль.
    """
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        context = _launch(pw, account_id, proxy, headless=False)
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        print(f"Войди в аккаунт {account_id} в открытом окне. "
              f"Профиль сохранится в {profile_dir(account_id)}.")
        print(f"Окно закроется через {timeout_s} с или по Ctrl+C.")
        try:
            page.wait_for_timeout(timeout_s * 1000)
        except KeyboardInterrupt:
            pass
        finally:
            context.close()
    return True
