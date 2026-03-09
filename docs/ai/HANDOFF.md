# Handoff

- Current branch: `main`
- Open work:
  - None.
- Context:
  - Default no-arg startup still launches the `Textual` TUI, but the sidebar now centers on stored transcriptions instead of unread/read queue state.
  - The TUI in `tui.py` now uses a roughly `4fr / 3fr` layout, focuses the transcription list on mount for immediate arrow-key previewing, and exposes source selection in the `Recording Mode` card for microphone vs filesystem file transcription.
  - `PromptManager` in `main.py` no longer uses `played_count`; stored prompts are plain history entries, `--query` deletes the oldest prompt, and old databases are migrated in place.
  - TUI user choices now persist directly to `CONFIG_FILE`: preprocessing mode defaults to `english`, source mode and last file path are remembered, model edits persist, and queue storage is always on.
  - Clipboard support now uses system tools from `tui.py:25` and `tui.py:70`, with OSC52 fallback when external helpers are unavailable.
  - File transcription inside the TUI is handled by a dedicated `process_file_for_tui()` path in `main.py`, and temp recording copies now use 3-digit version suffixes like `v001`.
