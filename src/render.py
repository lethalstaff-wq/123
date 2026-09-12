"""Рендер видео через ffmpeg.

Ключевая идея: НЕ существует «одного файла на 20 аккаунтов». Каждый VideoPlan
собирается из ассетов заново, а variant_seed управляет всеми осями вариативности:
какие отрезки клипов, порядок, темп, зум, цветокоррекция, шрифт, позиция и стиль
текста, музыка, длительность. Два плана с разным seed дают разные файлы с разными
хешами и разной визуальной динамикой.
"""
from __future__ import annotations

import hashlib
import json
import random
import shlex
import subprocess
from pathlib import Path
from typing import Sequence

from .config import settings
from .models import Asset, RenderResult, VideoPlan, utcnow

W, H, FPS = 1080, 1920, 30

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]

# Оси вариативности. Меняются вместе с seed — см. SPEC.md «Уникализация».
SPEEDS = [0.94, 0.97, 1.0, 1.03, 1.06, 1.1]
ZOOMS = [1.0, 1.04, 1.08, 1.12]
GRADES = [
    "eq=contrast=1.0:saturation=1.0",
    "eq=contrast=1.06:saturation=1.08",
    "eq=contrast=1.1:saturation=0.95:gamma=1.03",
    "eq=contrast=0.97:saturation=1.15",
    "curves=preset=lighter",
]
HOOK_Y = ["h*0.08", "h*0.12", "h*0.16", "h*0.72"]
HOOK_SIZE = [64, 72, 80, 88]
BOX_STYLES = [
    dict(box=1, boxcolor="black@0.55", boxborderw=18, fontcolor="white"),
    dict(box=1, boxcolor="black@0.75", boxborderw=24, fontcolor="white"),
    dict(box=0, boxcolor="black@0", boxborderw=0, fontcolor="white"),
    dict(box=1, boxcolor="#0b0b0b@0.6", boxborderw=20, fontcolor="#ffe14d"),
]


class RenderError(RuntimeError):
    pass


def _font() -> str:
    for p in FONT_CANDIDATES:
        if Path(p).exists():
            return p
    raise RenderError(
        "Не найден TTF-шрифт для drawtext. Поставь fonts-dejavu или задай путь "
        "в FONT_PATH и добавь его в FONT_CANDIDATES."
    )


def probe_duration(path: str) -> float:
    cfg = settings()
    out = subprocess.run(
        [cfg.ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=False,
    )
    try:
        return float(out.stdout.strip())
    except ValueError:
        raise RenderError(f"ffprobe не смог прочитать длительность: {path}\n{out.stderr[:400]}")


def esc(text: str) -> str:
    """Экранирование для drawtext: двоеточие, кавычки, перенос, процент."""
    return (
        text.replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "’")
        .replace("%", "\\%")
        .replace(",", "\\,")
        .replace("\n", " ")
    )


def wrap(text: str, per_line: int = 22) -> str:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= per_line:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return "\n".join(lines[:4])


def _segment_plan(assets: Sequence[Asset], total: float, rng: random.Random) -> list[tuple[Asset, float, float]]:
    """Делит целевую длительность между клипами и выбирает случайные отрезки внутри каждого."""
    n = max(1, len(assets))
    base = total / n
    plan: list[tuple[Asset, float, float]] = []
    for a in assets:
        dur = a.duration_s or probe_duration(a.path)
        seg = min(max(base * rng.uniform(0.8, 1.2), 1.2), max(dur - 0.2, 1.0))
        start = rng.uniform(0, max(dur - seg - 0.1, 0)) if dur > seg + 0.2 else 0.0
        plan.append((a, round(start, 2), round(seg, 2)))
    return plan


def build_command(plan: VideoPlan, assets: Sequence[Asset], out_path: Path,
                  music: Asset | None = None) -> list[str]:
    cfg = settings()
    rng = random.Random(plan.variant_seed)
    font = _font()
    speed = rng.choice(SPEEDS)
    zoom = rng.choice(ZOOMS)
    grade = rng.choice(GRADES)
    segs = _segment_plan(assets, plan.target_duration_s * speed, rng)

    cmd: list[str] = [cfg.ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for a, start, seg in segs:
        cmd += ["-ss", f"{start}", "-t", f"{seg}", "-i", a.path]
    if music:
        cmd += ["-i", music.path]

    parts: list[str] = []
    for i, (_a, _s, _seg) in enumerate(segs):
        # кроп в 9:16 с небольшим зумом + лёгкая цветокоррекция: у каждого варианта своя картинка
        parts.append(
            f"[{i}:v]scale={int(W*zoom)}:{int(H*zoom)}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},setsar=1,fps={FPS},{grade}[v{i}]"
        )
    concat_in = "".join(f"[v{i}]" for i in range(len(segs)))
    parts.append(f"{concat_in}concat=n={len(segs)}:v=1:a=0[cat]")
    if abs(speed - 1.0) > 0.001:
        parts.append(f"[cat]setpts={1/speed:.4f}*PTS[sp]")
        last = "sp"
    else:
        last = "cat"

    style = rng.choice(BOX_STYLES)
    hook = wrap(plan.hook_text)
    box = (f"box={style['box']}:boxcolor={style['boxcolor']}:boxborderw={style['boxborderw']}"
           if style["box"] else "box=0")
    parts.append(
        f"[{last}]drawtext=fontfile={font}:text='{esc(hook)}':"
        f"fontsize={rng.choice(HOOK_SIZE)}:fontcolor={style['fontcolor']}:{box}:"
        f"x=(w-text_w)/2:y={rng.choice(HOOK_Y)}:line_spacing=10:"
        f"enable='between(t,0,{rng.uniform(2.2, 3.6):.2f})'[hk]"
    )
    last = "hk"

    # тело: биты формата выводятся по очереди — это и удержание, и уникальность текста
    beats = [b for b in (plan.body_beats or []) if b][:3]
    if beats:
        step = max((plan.target_duration_s - 3.0) / len(beats), 1.5)
        t = 3.0
        for j, beat in enumerate(beats):
            parts.append(
                f"[{last}]drawtext=fontfile={font}:text='{esc(wrap(beat, 26))}':"
                f"fontsize=56:fontcolor=white:box=1:boxcolor=black@0.5:boxborderw=14:"
                f"x=(w-text_w)/2:y=h*0.78:line_spacing=8:"
                f"enable='between(t,{t:.2f},{t+step:.2f})'[b{j}]"
            )
            last = f"b{j}"
            t += step

    if plan.cta_text:
        parts.append(
            f"[{last}]drawtext=fontfile={font}:text='{esc(plan.cta_text)}':"
            f"fontsize=52:fontcolor=white:box=1:boxcolor=black@0.6:boxborderw=16:"
            f"x=(w-text_w)/2:y=h*0.88:"
            f"enable='gte(t,{max(plan.target_duration_s - 4.0, 1.0):.2f})'[out]"
        )
        last = "out"

    filter_complex = ";".join(parts)
    cmd += ["-filter_complex", filter_complex, "-map", f"[{last}]"]
    if music:
        vol = rng.uniform(0.35, 0.7)
        cmd += ["-map", f"{len(segs)}:a", "-af", f"volume={vol:.2f},afade=t=out:st="
                f"{max(plan.target_duration_s - 1.2, 0.5):.2f}:d=1.2", "-shortest"]
    cmd += [
        "-t", f"{plan.target_duration_s:.2f}",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", str(rng.choice([20, 21, 22])),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        str(out_path),
    ]
    return cmd


def render(plan: VideoPlan, assets: Sequence[Asset], music: Asset | None = None) -> RenderResult:
    cfg = settings()
    out_dir = Path(cfg.out_dir) / plan.geo / plan.platform.value / plan.slot_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{plan.plan_id}.mp4"

    cmd = build_command(plan, assets, out_path, music)
    if cfg.dry_run:
        (out_dir / f"{plan.plan_id}.cmd.txt").write_text(shlex.join(cmd), encoding="utf-8")
        return RenderResult(plan.plan_id, str(out_path), None, plan.target_duration_s,
                            W, H, checksum="dry-run", rendered_at=utcnow())

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 or not out_path.exists():
        raise RenderError(f"ffmpeg упал на {plan.plan_id}:\n{res.stderr[-1500:]}")

    thumb = out_dir / f"{plan.plan_id}.jpg"
    subprocess.run(
        [cfg.ffmpeg, "-y", "-loglevel", "error", "-ss", "1", "-i", str(out_path),
         "-frames:v", "1", "-q:v", "3", str(thumb)],
        capture_output=True, check=False,
    )
    digest = hashlib.sha256(out_path.read_bytes()).hexdigest()
    return RenderResult(
        plan_id=plan.plan_id, video_path=str(out_path),
        thumb_path=str(thumb) if thumb.exists() else None,
        duration_s=probe_duration(str(out_path)), width=W, height=H,
        checksum=digest, rendered_at=utcnow(),
    )


def write_post_kit(plan: VideoPlan, rr: RenderResult, account_username: str | None) -> Path:
    """Пост-кит для режима KIT: всё, что нужно человеку/устройству, одним json + текстовым файлом."""
    d = Path(rr.video_path).parent
    kit = {
        "plan_id": plan.plan_id,
        "platform": plan.platform.value,
        "geo": plan.geo,
        "account": account_username,
        "publish_at_utc": plan.scheduled_for_utc,
        "video": rr.video_path,
        "thumbnail": rr.thumb_path,
        "caption": plan.caption,
        "title": plan.title,
        "hashtags": plan.hashtags,
        "cta": plan.cta_text,
        "checklist": [
            "залить с устройства/сессии, привязанной к этому аккаунту",
            "подпись вставить целиком, хештеги не менять",
            "после публикации записать ссылку: cli.py record-post",
        ],
    }
    p = d / f"{plan.plan_id}.kit.json"
    p.write_text(json.dumps(kit, ensure_ascii=False, indent=2), encoding="utf-8")
    (d / f"{plan.plan_id}.caption.txt").write_text(
        f"{plan.caption}\n\n{' '.join('#' + h.lstrip('#') for h in plan.hashtags)}",
        encoding="utf-8",
    )
    return p
