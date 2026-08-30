# Conventions

Coding patterns, naming rules, and style agreements for this project.
Follow these without question. Do not deviate unless explicitly told.

## Naming
- LLM prompts are stored in `~/.config/aitranscribe/prompts.toml` (TOML format). All prompt text is configurable; the file is auto-created from embedded defaults if missing.
- Use `{{variable}}` double-mustache placeholders in prompt templates, resolved via `str.replace()`.
- Keep user-facing labels for preprocessing modes identical between the `Recording Mode` radio buttons and README/help text.

## File Layout
- Keep the `Textual` UI in `tui.py` and keep API, recording, and persistence helpers in `main.py` until a larger refactor is requested.

## API Patterns
- Never use `assert` for runtime validation in production code (`python -O` strips asserts and missing-API-key errors lose all context). Use `require_stt_client()` / `require_llm_client()` from `main.py` instead of touching the module-level `stt_client` / `llm_client` singletons directly; they raise `RuntimeError` with user-facing messages shared with `validate_api_keys()`.
- For TUI-triggered transcription work, send progress through the four high-level feedback IDs `compress`, `transcribe`, `post_process`, and `summary`, and use a separate transcript callback to surface raw STT text before post-processing finishes.
- `process_with_llm(client, messages, llm_model)` accepts pre-built `messages: list[dict]` and does not construct prompts internally. Use `build_post_process_messages`, `build_summary_messages`, or `build_translate_messages` to assemble messages before calling it.
- The translation sub-template (`{{translate}}` in the post_process user template) is resolved before injection — when no translation is requested, the placeholder is replaced with an empty string, keeping exactly 2 messages to the LLM.

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
- Keep TUI mode state and user feedback separate: the left status field shows derived `Command Mode` / `Pane Focus Mode` plus activity, and the right flash field shows the latest action confirmation or error.
- In append mode, use the selected saved transcription as the render and persistence source of truth instead of transient editor text.

## Pane Focus Mode
- When a user clicks in a pane during pane focus mode, perform the action and then immediately return to command mode.
- Exception: Filesystem file selection stays in pane mode so the user can enter the file path.
- Call `action_enter_command_mode()` after the action completes, not instantly on click.

## Error Handling
- Never use `pass` in an `except` block — exceptions must always be user-visible.
- In TUI mode, use `ErrorDialog(title, message, detail, fatal)` for errors the user must acknowledge.
  - `fatal=True`: config/setup errors → app exits after OK.
  - `fatal=False`: transient errors (network, transcription) → app continues.
- In CLI mode, use `console.print()` for warnings/errors.
- In `core.py` library functions, let exceptions propagate to callers who decide the UI treatment.
- Windows-only DLL path additions (`os.add_dll_directory`) are exempt — they are expected failures on non-Windows.

## Testing
- Cover TUI integration points from the CLI layer with focused unit tests instead of trying to run an interactive terminal session in `pytest`.
- Add focused unit tests for clipboard fallback helpers and TUI state-selection behavior instead of trying to verify them through live terminal automation.
