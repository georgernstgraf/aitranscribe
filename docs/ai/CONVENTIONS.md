# Conventions

Coding patterns, naming rules, and style agreements for this project.
Follow these without question. Do not deviate unless explicitly told.

## Naming
- Keep TUI preprocessing modes centralized in `PRE_PROCESS_MODES` and derive prompt text from that mapping instead of duplicating strings.
- Keep user-facing labels for preprocessing modes identical between `PRE_PROCESS_MODES`, the `Recording Mode` radio buttons, and README/help text.

## File Layout
- Keep the `Textual` UI in `tui.py` and keep API, recording, and persistence helpers in `main.py` until a larger refactor is requested.

## API Patterns
- For TUI-triggered transcription work, send progress through the four high-level feedback IDs `compress`, `transcribe`, `post_process`, and `summary`, and use a separate transcript callback to surface raw STT text before post-processing finishes.

## Database
- Keep prompt summaries nullable in SQLite and migrate older `prompts` tables in place by adding `summary` instead of rebuilding the whole database when only that column is missing.

## UI Patterns
- Wrap transcript and preview text to the actual panel width; do not reintroduce fixed-width wrapping like the removed 68-character limit.
- Use `Checkbox` for compact boolean settings in the sidebar instead of `Switch`, which rendered and behaved poorly in this layout.
- Drive stored-transcription navigation with `OptionList`; the highlighted entry is the source of truth for transcript preview while the app is idle.
- Keep the transcription list focused on mount so arrow keys work immediately when the app opens.
- The `Transcriptions` pane should show the full stored history ordered newest-first and expand to fill the sidebar height left over after `Recording Mode` and `Configuration` take their fixed space.
- The `Transcriptions` pane should prefer stored `summary` text for list rows and fall back to shortened full transcript text only while a summary is still missing.
- Compute history-row truncation from the live `OptionList` content width so startup layout does not add ellipses before the sidebar has reached its real size.
- After the initial mount refresh, schedule one extra `refresh_history()` after the first layout pass so startup truncation uses the same width logic as later post-transcription refreshes.
- Keep source selection and file-path entry inside the `Recording Mode` panel; microphone and filesystem transcription are two inputs to the same workflow.
- Persist user-adjustable TUI choices directly to `CONFIG_FILE` instead of keeping them session-local.

## Testing
- Cover TUI integration points from the CLI layer with focused unit tests instead of trying to run an interactive terminal session in `pytest`.
- Add focused unit tests for clipboard fallback helpers and TUI state-selection behavior instead of trying to verify them through live terminal automation.
