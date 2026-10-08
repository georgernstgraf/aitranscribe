# Handoff

## 2026-10-08 session: crafted system prompt adopted (#81)
- `_DEFAULT_PROMPTS_TOML` `[post_process.system]` = the polished-recognition
  #112 crafted prompt (prompts.json, v1.3.5), adapted to desktop (no
  "smartphone user"), injection guard line kept.
- `_upgrade_legacy_prompt_defaults` now chains TWO generations: gen 1
  (pre-#73, soft translate + pre-guard system) and gen 2 (#73..#80,
  hardened translate + keyboard-era system, new constant
  `_LEGACY_POST_PROCESS_SYSTEM`). Pristine files of either generation are
  rewritten from the template; partially customized files get the system
  prompt patched in memory.
- Tests 196 passed (3 new: crafted markers, keyboard-era rewrite,
  keyboard-era in-memory upgrade). Commit c55f441. Sub-issue of
  polished-recognition#115.

No pending implementation tasks. 2026-10-04 session added Escape-cancel and
P pause/resume to the TUI recording workflow.

## 2026-10-04 session: TUI recording controls
- `tui.py`:
  - `Binding("escape", "escape_key", ...)`; `action_escape_key()` cancels an
    active recording (`cancel_recording()`) or returns to Command Mode.
  - `cancel_recording()` stops the recorder, discards audio, clears append
    state, resets the transcript/feedback, and flashes the cancel message.
  - `RecordingController.paused` + `pause()`/`resume()`; callback drops frames
    while paused (stream stays open).
  - `Binding("p", "toggle_pause", ...)`; `action_toggle_pause()` is a no-op
    unless recording, toggles the recorder, and updates state/flash.
  - State label: `… Press P to Pause, Space to Finish` (or `Press P to Resume`
    while paused).
- `README.md`: keybinding table (new `P` row, updated `Escape` row) and
  Recording-modes note.
- Tests: `tests/test_tui.py` updated/added (Escape cancel, Append-mode cancel,
  Escape fallback, P toggle, P idle no-op, controller pause discard).
- Verification: `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q` → 193 passed.

## Notes for the next agent
- Host has no `Xvfb`/`xvfb-run`; headless pytest works with `PYNPUT_BACKEND=dummy`.
- `P` is Command-Mode-only (consistent with `A`/`C`/`D`/`E`/`W`). While a pane is
  focused, `p` is typed into that widget.
- By design, width changes do not reflow already-stored transcripts (DECISIONS 2026-09-27).

Last cleared: 2026-10-04.
