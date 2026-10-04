# Project State

Current status as of 2026-10-04.

## Current Focus
TUI recording controls hardened: `Escape` aborts an active recording and
discards its audio, and a new `P` binding pauses/resumes dictation.

- `tui.py`: `Escape` binding renamed to `escape_key` → `action_escape_key()`,
  which calls the new `cancel_recording()` while `is_recording`, otherwise the
  existing `action_enter_command_mode()`.
- `RecordingController` gained a `paused` flag plus `pause()`/`resume()`; the
  audio callback skips frames while paused (stream stays open).
- `P` → `action_toggle_pause()` (Command-Mode-only, no-op when idle); the state
  label shows `Recording (paused): Press P to Resume, Space to Finish` and the
  flash field confirms the toggle.
- `README.md` keybinding table + Recording modes updated.

## Verification
- `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q`: 193 passed.
- New tests cover Escape-cancel (incl. Append mode), Escape fallback to Command
  Mode, P toggle/status text, P no-op when idle, and `RecordingController`
  frame discard during pause.

## Blockers
- None.

## Next Session Suggestion
- `DECISIONS.md` (now ~230 lines) still exceeds the 200-line guide; split by
  topic next time it is touched.
- Pre-existing watch item from #77 still open: a small-but-long file with
  failing `ffprobe` is returned unsplit by `chunk_audio`.
- `P` pause is TUI-only by decision; the legacy CLI recording path keeps
  Space-toggle / Escape-cancel only.
