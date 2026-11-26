---
type: State
title: Project State
description: "Current project status — overwritten on every persistence run."
tags: [aitranscribe]
generated: { by: opencode/knowledge-persistence, at: 2026-11-26T07:30:00Z }
verified: { by: opencode/knowledge-persistence, at: 2026-11-26T07:30:00Z }
status: stable
sources:
  - id: issue-92
    resource: https://github.com/georgernstgraf/aitranscribe/issues/92
    title: "ESC im Pane Focus Mode bricht laufende Diktat-Aufnahme ab"
---

# Project State

2026-11-26: Fixed #92 — ESC in Pane Focus Mode no longer cancels an active
recording. `action_escape_key` is two-stage: Pane Focus Mode → only
`set_focus(None)` (dictation keeps running); cancel-by-ESC stays exclusive to
Command Mode. Test
`test_escape_in_pane_focus_mode_during_recording_keeps_recording` pins the
contract. **355 tests pass.**

## Current Focus

Live fragmentation pipeline is stable (#88/#89/#90 shipped). The 2026-11-26
session touched only the TUI focus/ESC path (`tui.py`,
`tests/test_tui.py`) — no changes to `fragmenter.py`, `seam.py`, `main.py`
or `config.py` since 2026-11-02.

## Verification

- `./venv/bin/pytest -q`: **355 passed** (was 340).

## Blockers

- None.

## Next Session Suggestion

- Real microphone dictation on think/elite: confirm the TUI live partial text
  and measure stop→raw at the 45/5 defaults.
- `docs/ai/DECISIONS.md` is well over 200 lines — split by topic next touch
  (`DECISIONS-config.md`, `DECISIONS-audio.md`, `DECISIONS-prompts.md`).
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff
  for transient 429s; the live path validates API keys only after recording.
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
