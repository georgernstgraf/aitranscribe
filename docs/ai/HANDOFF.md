# Handoff

## 2026-11-02 session: seam conditioning (#89, follow-up of #88)
- Shipped `seam.py`: `seam_prompt()` (previous transcript tail, ≤96 chars,
  word-aligned) and `trim_echo()` (≤8 tokens, head token must match, ≤1
  mismatch for k≥2, no match keeps everything).
- `LiveTranscriptionSession._transcribe_loop` now composes `pre_roll +
  fragment` as one upload (1 s pre-roll), sends the prompt, and trims the echo
  against the **untrimmed** previous transcript. `core.transcribe_audio` gained
  `prompt` and `on_prompt_rejected` (HTTP 400 → retry bare, prompts off for the
  session).
- Log lines gained `prompt_chars` and `pre_roll_ms`.
- 331 tests green; real end-to-end against selfhosted-1 shows pre_roll 1000 ms,
  prompts 41–54 chars, no duplicated seam words.
- No pending implementation tasks.

## Notes for the next agent
- Never add a scope-level override (e.g. `[stt].model`): one value, one place —
  the profile owns its model, its upload ceilings and its `upload_format`.
- The fragmenter decides only when the full Suchfenster is recorded; the tail
  at the stop tap can therefore be `cut_interval + search_window` long. That is
  the stop→raw bound, not a bug.
- Echo trim compares against the untrimmed previous transcript; comparing
  against the trimmed text cascades (see PITFALLS).
- The seam measures are unconditional. The original's `Q < qualityMin` gate is
  intentionally not ported until there is data for it.
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

