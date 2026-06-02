"""Reframe 16:9 -> 9:16: нарезка исходного видео в вертикальные клипы 720x1280.

Часть пайплайна вертикальных видео (ContentFactory tsk-099, ADR-0003).
Две стратегии перевода широкого кадра в вертикаль, выбор на каждый сегмент:

- ``letterbox`` — видео целиком по ширине 720, сверху/снизу размытый фон до 1280.
  Интерфейс виден полностью, но мельче. Подходит почти всегда (дефолт).
- ``track`` — crop заданной области исходника, затем масштаб в 720x1280.
  Крупнее и читаемее, но теряет периферию; требует указания области.

Чистый ffmpeg через subprocess — moviepy не нужен. ffmpeg ищется в PATH
(или через переменную окружения FFMPEG).

Формат segments.txt (по строке на сегмент, ``#`` — комментарий)::

    # start-end,mode[,cx:cy:cw:ch]
    # start/end — секунды (float) или H:MM:SS(.ms); для track нужен crop
    0-15,letterbox
    0:00:20-0:00:35,track,320:0:1280:1080

Запуск::

    python reframe.py <video> <segments.txt> [--out output/clips]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

WIDTH = 720
HEIGHT = 1280
BLUR = "boxblur=20:2"  # размытие фона для letterbox


@dataclass
class Segment:
    """Один сегмент нарезки."""

    start: float
    end: float
    mode: str  # "letterbox" | "track"
    crop: tuple[int, int, int, int] | None  # (cx, cy, cw, ch) для track

    @property
    def duration(self) -> float:
        return round(self.end - self.start, 3)


def find_ffmpeg() -> str:
    """Найти исполняемый ffmpeg: переменная FFMPEG, затем PATH."""
    env = os.environ.get("FFMPEG")
    if env and Path(env).exists():
        return env
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError(
            "ffmpeg не найден. Добавьте его в PATH или задайте переменную окружения FFMPEG."
        )
    return found


def parse_time(value: str) -> float:
    """Разобрать время: секунды (``12.5``) или ``H:MM:SS(.ms)``."""
    value = value.strip()
    if ":" in value:
        parts = value.split(":")
        if len(parts) == 3:
            h, m, s = parts
        elif len(parts) == 2:
            h, m, s = "0", parts[0], parts[1]
        else:
            raise ValueError(f"Неверный формат времени: {value!r}")
        return int(h) * 3600 + int(m) * 60 + float(s)
    return float(value)


def parse_segments(path: str) -> list[Segment]:
    """Прочитать segments.txt в список сегментов (с валидацией)."""
    segments: list[Segment] = []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 2:
            raise ValueError(f"Строка {lineno}: ожидается 'start-end,mode[,crop]': {raw!r}")
        time_range, mode = parts[0], parts[1].lower()
        if "-" not in time_range:
            raise ValueError(f"Строка {lineno}: диапазон должен быть 'start-end': {time_range!r}")
        start_s, end_s = time_range.split("-", 1)
        start, end = parse_time(start_s), parse_time(end_s)
        if end <= start:
            raise ValueError(f"Строка {lineno}: end <= start ({start}..{end})")
        if mode not in ("letterbox", "track"):
            raise ValueError(f"Строка {lineno}: mode должен быть letterbox|track: {mode!r}")
        crop: tuple[int, int, int, int] | None = None
        if len(parts) >= 3 and parts[2]:
            coords = parts[2].split(":")
            if len(coords) != 4:
                raise ValueError(f"Строка {lineno}: crop = cx:cy:cw:ch: {parts[2]!r}")
            cx, cy, cw, ch = (int(c) for c in coords)
            crop = (cx, cy, cw, ch)
        if mode == "track" and crop is None:
            raise ValueError(f"Строка {lineno}: для mode=track обязателен crop cx:cy:cw:ch")
        segments.append(Segment(start, end, mode, crop))
    if not segments:
        raise ValueError(f"В {path} нет ни одного сегмента")
    return segments


def build_filter(seg: Segment) -> str:
    """Построить ffmpeg filter_complex для сегмента -> 720x1280."""
    if seg.mode == "letterbox":
        return (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},{BLUR}[bg];"
            f"[fg]scale={WIDTH}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )
    # track
    assert seg.crop is not None
    cx, cy, cw, ch = seg.crop
    return f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={WIDTH}:{HEIGHT},setsar=1[v]"


def reframe_segment(ffmpeg: str, video: str, seg: Segment, out_path: Path) -> None:
    """Вырезать и переформатировать один сегмент через ffmpeg."""
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
        # -ss и -t ДО -i (входные опции): с filter_complex выходной -t роняет видеопоток
        "-ss", f"{seg.start}", "-t", f"{seg.duration}", "-i", video,
        "-filter_complex", build_filter(seg),
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-movflags", "+faststart",
        str(out_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reframe 16:9 -> 9:16 (720x1280)")
    parser.add_argument("video", help="исходное видео")
    parser.add_argument("segments", help="segments.txt")
    parser.add_argument("--out", default="output/clips", help="папка для клипов")
    args = parser.parse_args()

    if not Path(args.video).is_file():
        print(f"Нет файла видео: {args.video}")
        return 1

    ffmpeg = find_ffmpeg()
    segments = parse_segments(args.segments)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.video).stem

    print(f"ffmpeg: {ffmpeg}\nсегментов: {len(segments)} -> {out_dir}")
    for i, seg in enumerate(segments, 1):
        out_path = out_dir / f"{stem}_{i:02d}_{seg.mode}.mp4"
        print(f"  [{i}/{len(segments)}] {seg.start}-{seg.end} {seg.mode} -> {out_path.name}")
        try:
            reframe_segment(ffmpeg, args.video, seg, out_path)
        except subprocess.CalledProcessError as e:
            print(f"     ОШИБКА ffmpeg (код {e.returncode}) на сегменте {i}")
            return 2
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
