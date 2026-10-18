# Project State

2026-10-18: Groq's long-upload text mangle fixed (words[] reconstruction +
120 s upload cap). Issue #83 closed, 208 tests pass.

## Current Focus
Umlaut words came back cut ("führen" -> "F") because Groq mangles the `text`
(and `segments[].text`) of uploads longer than ~120 s: every word loses its tail
from the first non-ASCII character on. `words[]` stays correct.

- `core.py`:
  - `transcribe_audio` requests `timestamp_granularities=["word"]`, rebuilds the
    transcript from the joined `words[]`, falls back to `text` when no words
    come back, and retries once without the parameter on `BadRequestError`.
  - `chunk_audio` default upload ceiling `GROQ_MAX_UPLOAD_S = 120` (was 600
    literal). Cut points are snapped into silencedetect pauses
    (`_snap_cut_points` / `_silence_midpoints` / `_parse_silence_midpoints`) and
    passed as `-segment_times`, with `-segment_time` as the no-cut fallback.
- `main.py`: `process_recorded_audio_for_tui` now passes `do_chunk=True` (was
  `False`), so microphone takes longer than 2 minutes are split too.
- `README.md`: chunking claims updated (2 minutes / 25 MB, pause-aligned cuts).

## Verification
- `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q`: **207 passed** (196 before, +11
  new: word-timestamp rebuild regression, text fallback, 400 retry, silence
  parser/snap units, cut snapping, boundary passthrough).
- Live Groq verification after the fix: `v166` (172 s, previously
  "machen w ich ... Git w ich nat ...") now returns "machen, würde ich eher
  sagen. In einem Git-Repository würde ich natürlich OpenCode oder ähnliches
  Zeugs"; `v189` (150 s) restores "ki-strategie.bmb.gv.at" and "23. Oktober
  möglich".
- Chunking on `v188` (394 s): 4 pause-aligned chunks (101/98/99/96 s, total
  394 s) whose seams land on word boundaries with intact umlauts.
- Diagnosis baseline (pre-fix): <=120 s clean vs >=122 s mangled, 134-394 s
  recordings of the owner all mangled, raw HTTP bytes confirmed server-side.

## Blockers
- None.

## Next Session Suggestion
- `DECISIONS.md` (231 lines) still exceeds the 200-line guide; split by topic
  next time it is touched.
- Pre-existing watch item: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio` (silently skips duration chunking).
- Latent charset hygiene, unrelated to this bug: `main.py:80/131` write the
  config without `encoding="utf-8"` (cp1252 default on Windows) and
  `tui.py:99` passes clipboard text through `subprocess` relying on the locale
  encoding.
- `transcribe_audio` still has no retry/backoff for transient Groq failures;
  HTTP 429 was hit repeatedly during diagnosis (the sister project retries 3x).
- Groq support report (same file: >120 s mangled, <=120 s clean, `words[]`
  correct) is still owed upstream.
