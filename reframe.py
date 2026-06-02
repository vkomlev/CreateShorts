"""Reframe 16:9 -> 9:16: нарезка исходного видео в вертикальные клипы 1080x1920.

Часть пайплайна вертикальных видео (ContentFactory tsk-099, ADR-0003).
Две стратегии перевода широкого кадра в вертикаль, выбор на каждый сегмент:

- ``letterbox`` — видео целиком по ширине 1080, сверху/снизу размытый фон до 1920.
  Интерфейс виден полностью, но мельче. Подходит почти всегда (дефолт).
- ``track`` — crop заданной области исходника, затем масштаб в 1080x1920.
  Крупнее и читаемее, но теряет периферию; требует указания области.

Чистый ffmpeg через subprocess — moviepy не нужен. ffmpeg ищется в PATH
(или через переменную окружения FFMPEG).

Формат segments.txt (по строке на сегмент, ``#`` — комментарий)::

    # start-end,mode[,cx:cy:cw:ch]
    # start/end — секунды (float) или H:MM:SS(.ms); для track нужен crop
    0-15,letterbox
    0:00:20-0:00:35,track,320:0:1280:1080

Запуск::

    python reframe.py <video> <segments.txt> [--srt subtitles.srt] [--out output/clips]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

WIDTH = 1080
HEIGHT = 1920
BLUR = "boxblur=20:2"  # размытие фона для letterbox
SUBTITLE_SAFE_MARGIN_PX = 700  # ContentFactory references/platforms/short-video.md
ASS_PLAY_RES_Y = 288  # libass SRT conversion grid; style values scale to the output height
SUBTITLE_MARGIN_V = round(SUBTITLE_SAFE_MARGIN_PX * ASS_PLAY_RES_Y / HEIGHT)
SUBTITLE_STYLE = (
    "FontName=Arial,FontSize=8,Alignment=2,"
    f"MarginV={SUBTITLE_MARGIN_V},Outline=1,Shadow=0"
)


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


@dataclass
class Cue:
    """Одна реплика субтитров."""

    start: float
    end: float
    text: str


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


def parse_srt_time(value: str) -> float:
    """Разобрать SRT-время ``H:MM:SS,mmm`` или ``HH:MM:SS,mmm``."""
    return parse_time(value.replace(",", "."))


def format_srt_time(value: float) -> str:
    """Нормализовать секунды в SRT-время ``HH:MM:SS,mmm``."""
    milliseconds = round(value * 1000)
    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"


def parse_srt(path: str | Path) -> list[Cue]:
    """Прочитать SRT без внешних зависимостей."""
    cues: list[Cue] = []
    blocks = Path(path).read_text(encoding="utf-8-sig").replace("\r\n", "\n").split("\n\n")
    for block in blocks:
        lines = block.strip().splitlines()
        if not lines:
            continue
        timing_index = 1 if len(lines) > 1 and "-->" in lines[1] else 0
        if "-->" not in lines[timing_index]:
            raise ValueError(f"Нет тайм-кода SRT в блоке: {block!r}")
        start_s, end_s = (part.strip() for part in lines[timing_index].split("-->", 1))
        text = "\n".join(lines[timing_index + 1 :]).strip()
        if not text:
            raise ValueError(f"Нет текста SRT в блоке: {block!r}")
        start, end = parse_srt_time(start_s), parse_srt_time(end_s)
        if end <= start:
            raise ValueError(f"Некорректный диапазон SRT: {start_s!r} --> {end_s!r}")
        cues.append(Cue(start, end, text))
    return cues


def slice_srt(cues: list[Cue], seg_start: float, seg_end: float) -> list[Cue]:
    """Обрезать реплики по сегменту и перенести начало сегмента к нулю."""
    sliced: list[Cue] = []
    for cue in cues:
        if cue.end > seg_start and cue.start < seg_end:
            sliced.append(
                Cue(
                    max(0, cue.start - seg_start),
                    min(cue.end, seg_end) - seg_start,
                    cue.text,
                )
            )
    return sliced


def write_srt(path: str | Path, cues: list[Cue]) -> None:
    """Записать нормализованный UTF-8 SRT."""
    blocks = [
        f"{index}\n{format_srt_time(cue.start)} --> {format_srt_time(cue.end)}\n{cue.text}"
        for index, cue in enumerate(cues, 1)
    ]
    Path(path).write_text("\n\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")


def escape_subtitles_path(path: str | Path) -> str:
    """Экранировать путь для ffmpeg subtitles= на Windows и POSIX."""
    return Path(path).resolve().as_posix().replace("\\", "/").replace(":", r"\:").replace("'", r"\'")


def parse_segments(path: str) -> list[Segment]:
    """Прочитать segments.txt в список сегментов (с валидацией)."""
    segments: list[Segment] = []
    for lineno, raw in enumerate(Path(path).read_text(encoding="utf-8-sig").splitlines(), 1):
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


def build_filter(seg: Segment, subtitles_path: str | Path | None = None) -> str:
    """Построить ffmpeg filter_complex для сегмента -> 1080x1920."""
    if seg.mode == "letterbox":
        reframe_filter = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={WIDTH}:{HEIGHT},{BLUR}[bg];"
            f"[fg]scale={WIDTH}:-2[fg];"
            f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,"
            f"trim=duration={seg.duration},setpts=PTS-STARTPTS[v]"
        )
    else:
        # track
        assert seg.crop is not None
        cx, cy, cw, ch = seg.crop
        reframe_filter = (
            f"[0:v]crop={cw}:{ch}:{cx}:{cy},scale={WIDTH}:{HEIGHT},setsar=1,"
            f"trim=duration={seg.duration},setpts=PTS-STARTPTS[v]"
        )
    if subtitles_path is None:
        return reframe_filter
    escaped_path = escape_subtitles_path(subtitles_path)
    return f"{reframe_filter};[v]subtitles=filename='{escaped_path}':force_style='{SUBTITLE_STYLE}'[vout]"


def reframe_segment(
    ffmpeg: str,
    video: str,
    seg: Segment,
    out_path: Path,
    subtitles_path: str | Path | None = None,
) -> None:
    """Вырезать и переформатировать один сегмент через ffmpeg."""
    cmd = [
        ffmpeg, "-y", "-hide_banner", "-loglevel", "error",
    ]
    if seg.start:
        cmd.extend(["-ss", f"{seg.start}"])
    cmd.extend([
        "-i", video,
        "-filter_complex", build_filter(seg, subtitles_path),
        "-map", "[vout]" if subtitles_path else "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-af", f"atrim=duration={seg.duration},asetpts=PTS-STARTPTS",
        "-c:a", "aac", "-movflags", "+faststart",
        str(out_path),
    ])
    subprocess.run(cmd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Reframe 16:9 -> 9:16 (1080x1920)")
    parser.add_argument("video", help="исходное видео")
    parser.add_argument("segments", help="segments.txt")
    parser.add_argument("--srt", help="SRT-субтитры для прожига в клипы")
    parser.add_argument("--out", default="output/clips", help="папка для клипов")
    args = parser.parse_args()

    if not Path(args.video).is_file():
        print(f"Нет файла видео: {args.video}")
        return 1
    if args.srt and not Path(args.srt).is_file():
        print(f"Нет файла субтитров: {args.srt}")
        return 1

    ffmpeg = find_ffmpeg()
    segments = parse_segments(args.segments)
    cues = parse_srt(args.srt) if args.srt else None
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(args.video).stem

    print(f"ffmpeg: {ffmpeg}\nсегментов: {len(segments)} -> {out_dir}")
    with tempfile.TemporaryDirectory(prefix="reframe_") as temp_dir:
        for i, seg in enumerate(segments, 1):
            out_path = out_dir / f"{stem}_{i:02d}_{seg.mode}.mp4"
            print(f"  [{i}/{len(segments)}] {seg.start}-{seg.end} {seg.mode} -> {out_path.name}")
            subtitles_path = None
            if cues is not None:
                segment_cues = slice_srt(cues, seg.start, seg.end)
                if segment_cues:
                    subtitles_path = Path(temp_dir) / f"segment_{i:02d}.srt"
                    write_srt(subtitles_path, segment_cues)
            try:
                reframe_segment(ffmpeg, args.video, seg, out_path, subtitles_path)
            except subprocess.CalledProcessError as e:
                print(f"     ОШИБКА ffmpeg (код {e.returncode}) на сегменте {i}")
                return 2
    print("Готово.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
