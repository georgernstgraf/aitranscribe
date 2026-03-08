# Handoff

- Current branch: `main`
- Open work:
  1. [ ] See #42 - Finish the TUI-first transcription workflow rollout and manual validation.
- Context:
  - Default no-arg startup now launches the `Textual` TUI from `main.py:605` via `launch_tui()` in `main.py:539`.
  - The new UI lives in `tui.py:56` and currently covers microphone recording, transcript display, the four-line feedback log, preprocessing mode selection, extra settings, unread history, and mark-all-read.
  - Queue helpers for unread counts, recent unread items, and mark-all-read were added to `PromptManager` in `main.py:346`, `main.py:374`, and `main.py:461`.
  - Remaining work is primarily manual UX validation, deciding how aggressively to retire legacy CLI switches once the TUI path is stable, and addressing the new requirement that transcript text must be mouse-copyable for paste into other applications.
