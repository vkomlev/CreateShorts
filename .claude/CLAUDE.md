# Claude Code — Make_video

## Стек
- Python, moviepy, ffmpeg

## Контекст проекта
Сборка коротких вертикальных видео (720×1280, до ~60 с) из кадров, аудио, субтитров.
Два сценария: слайд-видео (`create_video.py`) и видео с набором кода (`create_video_code.py`).

## Структура каталога
- `create_video.py` — слайд-видео: `layouts.txt` + `subtitles.srt` + `audio.mp3`
- `create_video_code.py` — видео набора кода: `code.txt` + `audio.mp3`
- `layouts.txt` — таймлайн слайдов: `начало-конец,путь_к_изображению`
- `images/` — кадры для слайд-видео
- `output_video.mp4` — результат обоих скриптов (перезаписывается)

## Указатели
- `docs/ai/PROJECT_MEMORY.md` — durable-память (риски, smoke-проверки, решения). Общая с Codex
- `README.md`, `docs/usage.md` — human-слой: запуск, форматы входов, константы
- `AGENTS.md` — Codex-якорь (список skills)

---

## Профиль: Video Builder

**Scope:** `create_video.py`, `create_video_code.py`

**Валидация:**
```powershell
python -m compileall create_video.py create_video_code.py
```

**Runtime:**
- Проверить наличие input assets: `audio.mp3`, `subtitles.srt`, `images/`, `layouts.txt`
- Output filename — всегда явно (избегать перезаписи)

**Контракт вывода:**
- `Plan`
- `Changed Files`
- `Validation Commands`
- `Asset Checks`
- `Risks`

---

## Общие правила
- Secrets только в `.env`, не в коде
- `/review-gate` обязателен перед интеграцией в main/master
- Глобальный контекст: `~/.claude/CLAUDE.md`
