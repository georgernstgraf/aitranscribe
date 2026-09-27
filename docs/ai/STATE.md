# Project State

Current status as of 2026-09-27.

## Current Focus
Configurable output line wrapping (0 off / 80 default / 120), implemented and green.

- `wrap_text(text, max_length=None)` (main.py) now uses `textwrap`, resolves `max_length` from the `OUTPUT_WIDTH` module global, treats `0` as off, and is line-preserving + idempotent (only overlong lines are wrapped; existing `\n` survive; unbreakable tokens stay intact).
- `OUTPUT_WIDTH` is loaded in `init_app()`, written by `_create_default_config`, and appended by `_MIGRATION_BLOCKS` for existing configs; `get_tui_settings()` exposes `output_width` and `persist_tui_setting("output_width", ...)` updates the global + config.
- CLI: new `--width`/`-w` option (accepts 0/80/120 only, else exit 1); it overrides the run's width and is forwarded to the TUI session via `launch_tui(width_override=...)`.
- Storage: `PromptManager.add_prompt`/`update_prompt` wrap at the storage boundary, so CLI, TUI manual saves, append, and translate are all covered.
- TUI: new compact "Output width" RadioSet (Off/80/120) in the Configuration panel, persisted on change; `apply_output_width()` wraps displayed text via an injected `wrap_output` callback; `refresh_transcript()` applies the current width.

## Verification
- Full suite (headless, `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q`): 186 passed, 1 skipped.
- Note: no `Xvfb`/`xvfb-run` on this host; `PYNPUT_BACKEND=dummy` was used instead of the documented xvfb-run (see HANDOFF/PITFALLS).

## Blockers
- None.

## Next Session Suggestion
- Width changes do not reflow already-stored entries (by design, DECISIONS 2026-09-27). Revisit only if users ask for reflow.
- `DECISIONS.md` is slightly over the 200-line guide; split by topic next time it is touched.
- Pre-existing watch item from #77 still open: a small-but-long file with failing `ffprobe` is returned unsplit by `chunk_audio`.
