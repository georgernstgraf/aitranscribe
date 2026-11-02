# Handoff

## 2026-11-02 session: Q-gate for seam conditioning (#90, follow-up of #89)
- `fragmenter.Fragment.silence_aligned` is now derived (`quality > 0`); the
  stored field is gone. `prepare_tail_sync` still commits the tail with Q = 0.
- `seam.trim_echo` returns `(text, removed_tokens)`.
- `LiveTranscriptionSession._transcribe_loop` evaluates the gate per seam:
  `seam_quality = previous_quality` (fragment i−1's end cut; 0 for fragment 0),
  `conditioned = index > 0 and seam_quality < CONFIG.recording.seam_quality_min`.
  Pre-roll, prompt and trim are applied only when conditioned; `previous_text`
  and `previous_tail` are maintained for every fragment so a later conditioned
  seam still has context.
- `config.RecordingSettings.seam_quality_min` (default 10, `>= 0`) is parsed,
  rendered in `render_document`/`config.example.toml` with a comment block and
  shown in `config show`.
- STT request lines gained `seam_quality`, `conditioned`, `echo_trimmed_tokens`.
- 340 tests green (was 331). No pending implementation tasks.

## Notes for the next agent
- Never add a scope-level override (e.g. `[stt].model`): one value, one place —
  the profile owns its model, its upload ceilings and its `upload_format`.
- The fragmenter decides only when the full Suchfenster is recorded; the tail
  at the stop tap can therefore be `cut_interval + search_window` long. That is
  the stop→raw bound, not a bug.
- Echo trim compares against the untrimmed previous transcript; comparing
  against the trimmed text cascades (see PITFALLS).
- The gate is strict `<`: `seam_quality_min = 0` disables conditioning, and a
  seam at exactly the threshold stays naked.
- A naked seam must never trim — without pre-roll there is no echo.
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
