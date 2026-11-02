# Handoff

## 2026-11-02 session: live fragmentation + per-fragment STT logging (#88)
- Shipped the port of polished-recognition's `FragmentPreparer`:
  `fragmenter.py` (SilenceQuality + worker loop), `main.LiveTranscriptionSession`,
  `main.process_live_recording`, `stt_log.py`, `[recording]` config section and
  `upload_format` on the STT profile.
- Capture is now 16 kHz mono; the TUI streams into the session instead of
  buffering the take. `--file` still uses the post-hoc `chunk_audio` path.
- Glossary: `CONTEXT.md` (Fragmenttakt, Suchfenster, Fragment, Festschreibung,
  erzwungener Schnitt, Restfragment, Q). No guard zone / LATE_HALF by design.
- 311 tests green (was 257); real end-to-end against selfhosted-1 verified.
- No pending implementation tasks. #89 (seam conditioning) is the open
  follow-up sub-issue; do not close #88 before it.

## Notes for the next agent
- Never add a scope-level override (e.g. `[stt].model`): one value, one place —
  the profile owns its model, its upload ceilings and its `upload_format`.
- The fragmenter decides only when the full Suchfenster is recorded; the tail
  at the stop tap can therefore be `cut_interval + search_window` long. That is
  the stop→raw bound, not a bug.
- `console.print` needs `markup=False` for anything containing `[stt]`-style
  text, otherwise Rich eats the brackets.
- `main.get_tui_settings()` reloads from `CONFIG_FILE`; tests only need to
  patch `main.CONFIG_FILE`, not the `CONFIG` global.
- Tests must go through `tests/conftest.py`'s isolated paths (now including
  `STT_LOG_FILE`); do not "fix" `CONFIG_DIR` by adding a production env
  override without a decision entry.
- `python-dotenv` is migration-only now (one release of grace, then remove).
- `docs/ai/DECISIONS.md` should be split by topic next touch.
- Host has no `Xvfb`/`xvfb-run`; headless pytest works with
  `PYNPUT_BACKEND=dummy` (not needed here — the suite ran without it).

Last cleared: 2026-11-02.
