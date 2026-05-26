# Project Memory

Project: Make_video
Path: `d:\Work\Make_video`
Created: 2026-05-26
Profile updated: 2026-05-27

## Purpose

- Responsible for generating short vertical videos from local inputs: slide/image timelines, subtitles, audio, and Python code demos.
- Not responsible for transcription, source content strategy, publishing, or long-term media asset management.

## AI-Facing Profile

- Stack: Python, moviepy, pillow, pysrt, Pygments, html2image/imgkit, imageio-ffmpeg.
- Output format is vertical short video: `720x1280`, usually capped around 58-60 seconds.
- Main scripts:
  - `create_video.py`: builds a slide-based video from `layouts.txt`, optional `subtitles.srt`, and `audio.mp3`.
  - `create_video_code.py`: builds a code-typing style video from `code.txt` and `audio.mp3`.
- Default output: `output_video.mp4`.
- Expected local input files are project-root files, not command-line arguments.

## Durable Context

- `layouts.txt` is a CSV-like timeline: `start-end,image_path` per line.
- `subtitles.srt` is read with `pysrt`; subtitle style is currently hardcoded in `create_video.py`.
- `create_video_code.py` converts syntax-highlighted Python HTML to `temp.png`; it depends on local HTML-to-image tooling.
- `audio.mp3`, `code.txt`, `layouts.txt`, `subtitles.srt`, images, temporary PNGs, and generated MP4s can be large or transient.

## Commands

- Setup: `python -m venv .venv`; `.venv\Scripts\activate`; `pip install -r requirements.txt`.
- Slide video: `python create_video.py`.
- Code demo video: `python create_video_code.py`.
- Smoke checks:
  - verify required inputs exist before running;
  - run on a tiny sample input first;
  - confirm `output_video.mp4` exists and has non-zero size;
  - open the first/last few seconds manually when visual layout or subtitles matter.

## Required Skills

- Use `qa-report` for report-only verification of generated video artifacts.
- Use `qa-fix` for fixing broken generation, missing inputs, bad subtitles, or output failures.
- Use `encoding-guard` for subtitle/code/text files with Cyrillic or mixed encodings.
- Use `project-docs` when changing input conventions or README/docs.
- Use `review-gate` before relying on a new video pipeline for repeated production use.

## Architecture Notes

- Core modules: `create_video.py`, `create_video_code.py`.
- Data/storage: local input files in project root; generated `output_video.mp4`; transient `temp.png`.
- External tools: ffmpeg through moviepy/imageio; imgkit may require wkhtmltoimage or equivalent local binary depending on environment.
- Trust boundaries: local file paths, generated media artifacts, temporary files, and any voice/audio assets supplied by the operator.

## Known Risks

- Reliability: missing local inputs, broken image paths, ffmpeg/imgkit binary availability, font availability, and memory use on large media.
- Security/privacy: audio, code, screenshots, and generated videos may contain private content; do not copy media contents into docs.
- Data/encoding: `subtitles.srt`, `code.txt`, and README text can hit encoding issues on Windows.
- Determinism: random transitions and typing delays make exact output non-deterministic unless code is adjusted.

## Smoke Checks

- `python create_video.py` with a tiny `layouts.txt`, `subtitles.srt`, `audio.mp3`, and image set.
- `python create_video_code.py` with a short `code.txt` and `audio.mp3`.
- Confirm output duration is within intended short-video limit.
- Confirm subtitles are readable and not clipped.
- Confirm temp files are removed after success/failure where applicable.

## Current Decisions

| Date | Decision | Why | Owner/Source |
| --- | --- | --- | --- |
| 2026-05-27 | Treat root input filenames as script contracts. | Current scripts read fixed filenames without CLI args. | Project profile |

## Prevention Register

| Date | Incident/Risk | Prevention Rule | Related Skill |
| --- | --- | --- | --- |
| 2026-05-27 | Video generation fails due to missing local input. | Preflight required files before running and report missing files explicitly. | `qa-report`, `qa-fix` |
| 2026-05-27 | Generated video has unreadable text/subtitles. | Include visual smoke check for first/last seconds and subtitle readability. | `qa-report` |

## Handoff Notes

- Current focus: small local scripts for short video assembly.
- Blockers: ffmpeg/imgkit/wkhtmltoimage availability and valid local media inputs.
- Follow-ups: consider adding CLI args and a sample fixture if this becomes a repeated pipeline.

## Maintenance Rules

- Keep durable facts here; keep transient task notes in session summaries or issue docs.
- Do not store credentials, tokens, cookies, personal secrets, or private keys.
- When implementation intentionally diverges from specs, record the decision and update the relevant specs/docs in the same task.
- Prefer links to canonical docs over duplicating long content.
