#!/usr/bin/env python3
"""Проверка движка браузерной публикации на локальном стенде.

Зачем: поток загрузки описан данными, и единственный способ убедиться, что движок
шагов (файл, текст, посимвольный ввод, клик, ожидание, проверка текста, скриншот)
работает — прогнать его против страницы, которую мы контролируем. Реальные
площадки здесь не трогаются.

Запуск: python scripts/smoke_browser.py
"""
from __future__ import annotations

import http.server
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.models import (Account, JobState, Platform, PublishMode,  # noqa: E402
                        RenderResult, VideoPlan, utcnow)
from src.publishers.base import PublishContext  # noqa: E402
from src.publishers.browser import BrowserPublisher  # noqa: E402

PORT = 8731
FIXTURES = ROOT / "tests" / "fixtures"


def serve() -> socketserver.TCPServer:
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(FIXTURES), **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def make_video(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
         "-i", "testsrc2=size=1080x1920:rate=30:duration=3",
         "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
         "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", str(path)],
        check=True,
    )


def main() -> int:
    video = ROOT / "out" / "_smoke" / "smoke.mp4"
    make_video(video)
    httpd = serve()
    try:
        plan = VideoPlan(
            plan_id="smoke-001", slot_id="us-tt-01", geo="us", platform=Platform.TIKTOK,
            format_id="before_after_fps",
            hook_text="40 to 55 fps on a GTX 1650 in Fortnite",
            cta_text="link in bio",
            caption="40 to 55 fps on a GTX 1650 in Fortnite (1080p, CapFrameX)",
            title="40 to 55 fps on a GTX 1650 in Fortnite",
            hashtags=["fps", "pcgaming"],
        )
        rr = RenderResult(plan_id=plan.plan_id, video_path=str(video), thumb_path=None,
                          duration_s=3.0, width=1080, height=1920,
                          checksum="smoke", rendered_at=utcnow())
        acct = Account(account_id="smoke-acct", slot_id="us-tt-01", platform=Platform.TIKTOK,
                       username="smoke", created_at=utcnow(), state="active")
        ctx = PublishContext(plan=plan, render=rr, account=acct, dry_run=False)

        pub = BrowserPublisher(platform_key="test_local", headless=True,
                               start_url=f"http://127.0.0.1:{PORT}/upload_page.html")
        res = pub.publish(ctx)
        print(f"состояние: {res.state.value}")
        if res.error:
            print(f"ошибка: {res.error}")
        shots = sorted((ROOT / "out" / "_browser" / plan.plan_id).glob("*.png"))
        print(f"скриншотов: {len(shots)}")
        for s in shots:
            print(f"  {s.name}: {s.stat().st_size} байт")
        return 0 if res.state == JobState.PUBLISHED else 1
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
