# Conventions

Coding patterns, naming rules, and style agreements for this project.
Follow these without question. Do not deviate unless explicitly told.

## Naming
- Keep TUI preprocessing modes centralized in `PRE_PROCESS_MODES` and derive prompt text from that mapping instead of duplicating strings.

## File Layout
- Keep the `Textual` UI in `tui.py` and keep API, recording, and persistence helpers in `main.py` until a larger refactor is requested.

## API Patterns
- For TUI-triggered transcription work, send progress through a callback keyed by the four fixed feedback IDs: `stt_send`, `stt_response`, `pre_send`, and `pre_response`.

## Testing
- Cover TUI integration points from the CLI layer with focused unit tests instead of trying to run an interactive terminal session in `pytest`.
