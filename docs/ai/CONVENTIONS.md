# Conventions

Coding patterns, naming rules, and style agreements for this project.
Follow these without question. Do not deviate unless explicitly told.

## Naming
- Keep TUI preprocessing modes centralized in `PRE_PROCESS_MODES` and derive prompt text from that mapping instead of duplicating strings.

## File Layout
- Keep the `Textual` UI in `tui.py` and keep API, recording, and persistence helpers in `main.py` until a larger refactor is requested.

## API Patterns
- For TUI-triggered transcription work, send progress through a callback keyed by the four fixed feedback IDs: `stt_send`, `stt_response`, `pre_send`, and `pre_response`.

## UI Patterns
- Wrap transcript and preview text to the actual panel width; do not reintroduce fixed-width wrapping like the removed 68-character limit.
- Use `Checkbox` for compact boolean settings in the sidebar instead of `Switch`, which rendered and behaved poorly in this layout.
- Drive stored-transcription navigation with `OptionList`; the highlighted entry is the source of truth for transcript preview while the app is idle.
- Keep the transcription list focused on mount so arrow keys work immediately when the app opens.
- The `Transcriptions` pane should show the full stored history ordered newest-first, not a small recent slice.
- Keep source selection and file-path entry inside the `Recording Mode` panel; microphone and filesystem transcription are two inputs to the same workflow.
- Persist user-adjustable TUI choices directly to `CONFIG_FILE` instead of keeping them session-local.

## Testing
- Cover TUI integration points from the CLI layer with focused unit tests instead of trying to run an interactive terminal session in `pytest`.
- Add focused unit tests for clipboard fallback helpers and TUI state-selection behavior instead of trying to verify them through live terminal automation.
