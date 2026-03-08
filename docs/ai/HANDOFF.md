# Handoff

- Current branch: `main`
- Open work:
  1. [ ] See #42 - Finish the TUI-first transcription workflow rollout and manual validation.
- Context:
  - Default no-arg startup now launches the `Textual` TUI from `main.py:603` via `launch_tui()` in `main.py:537`.
  - The new UI lives in `tui.py:120` and now covers microphone recording, transcript display, the four-line feedback log, preprocessing mode selection, compact checkbox-based settings, unread-history navigation, mark-all-read, and explicit transcript copy via `C`.
  - Queue helpers for unread counts, recent unread items, and mark-all-read were added to `PromptManager` in `main.py:346`, `main.py:374`, and `main.py:461`.
  - Clipboard support now uses system tools from `tui.py:25` and `tui.py:70`, with OSC52 fallback when external helpers are unavailable.
  - Unread previews are now driven by `OptionList` selection in `tui.py:306`, `tui.py:352`, `tui.py:390`, and `tui.py:558`, so arrow-key movement updates the full transcript panel.
  - Remaining work is primarily manual UX validation, deciding how aggressively to retire legacy CLI switches once the TUI path is stable, and further polishing the TUI layout and interaction model.
