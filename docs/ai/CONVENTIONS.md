# Conventions

Coding patterns, naming rules, and style agreements for this project.
Follow these without question. Do not deviate unless explicitly told.

## Naming
- Never include `codex`, `AI`, `KI`, `ChatGPT`, or similar assistant/tool branding in branch names, regardless of capitalization; use descriptive task-based names.
- LLM prompts are stored in `~/.config/aitranscribe/prompts.toml` (TOML format). All prompt text is configurable; the file is auto-created from embedded defaults if missing.
- Use `{{variable}}` double-mustache placeholders in prompt templates, resolved via `str.replace()`.
- Keep user-facing labels for preprocessing modes identical between the `Recording Mode` radio buttons and README/help text.

## File Layout
- Keep the `Textual` UI in `tui.py`, the configuration schema in `config.py`, and API/recording/persistence helpers in `main.py` until a larger refactor is requested.

## Initialization
- `main.py` import must stay side-effect-free. All setup (config create/migrate, `load_dotenv`, env constants, `PROMPTS`, OpenAI clients, `prompt_manager`) lives in the idempotent `init_app()`; `main()` calls it before any logic. Never add new module-level side effects.
- CLI option defaults that depend on initialized state (e.g. `stt_model`, `llm_model`) must default to `None` and be resolved inside `main()` after `init_app()`, because typer evaluates signature defaults at import time.
- Tests that call `init_app()` directly must restore all init-populated globals (see `_INIT_GLOBALS` in `tests/test_cli.py`) so later tests see consistent module state.
- `tests/conftest.py` runs the whole suite against a temporary config directory. A test that reloads `main` must not assume the module path constants survive — the autouse `_reassert_config_isolation` fixture restores them between tests.

## API Patterns
- Never use `assert` for runtime validation in production code (`python -O` strips asserts and missing-API-key errors lose all context). Use `require_stt_client()` / `require_llm_client()` from `main.py` instead of touching the module-level `stt_client` / `llm_client` singletons directly; they raise `RuntimeError` with user-facing messages shared with `validate_api_keys()`.
- All transcription work (chunk → STT → join → optional LLM) goes through `run_transcription_pipeline()` in `main.py`; never duplicate that sequence. Callbacks (`on_transcript`, `on_feedback`, `on_progress`) carry output; the pipeline itself never prints.
- `PromptManager` returns data (lists, bools, strings) and never prints; CLI rendering lives in `main.py` helpers (`print_stored_prompts`, `remove_prompt_by_index`).
- For TUI-triggered transcription work, send progress through the four high-level feedback IDs `compress`, `transcribe`, `post_process`, and `summary`, and use a separate transcript callback to surface raw STT text before post-processing finishes.
- `process_with_llm(client, messages, llm_model)` accepts pre-built `messages: list[dict]` and does not construct prompts internally. Use `build_post_process_messages`, `build_summary_messages`, or `build_translate_messages` to assemble messages before calling it.
- The translation clause travels in the **system** prompt (`{{target_language_clause}}`, filled from `[post_process.translate].prompt`), not in the user template. `build_post_process_messages()` substitutes only `{{text}}` in the user template; never reintroduce a `{{translate}}` placeholder there.

## Database
- Keep prompt summaries nullable in SQLite and migrate older `prompts` tables in place by adding `summary` instead of rebuilding the whole database when only that column is missing.

## UI Patterns
- Wrap preview text to the actual panel width; do not reintroduce hidden fixed-width limits. The only fixed-width wrapping is the explicit, user-controlled `OUTPUT_WIDTH` (`0`/`80`/`120`) applied through `wrap_text()` at output/storage boundaries.
- `wrap_text(text, max_length=None)` owns all line wrapping. It defaults to the `OUTPUT_WIDTH` module global, treats `0` as off, and is line-preserving (only overlong lines are wrapped, existing `\n` survive), so it is idempotent. Never re-implement ad-hoc wrapping.
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
- `PromptManager` methods must never catch-and-default on DB errors: let `sqlite3.Error` propagate. Callers own the UI treatment (ErrorDialog in TUI, console + exit in CLI). Empty-queue returns (`None`/`False`/`[]`) are legitimate values, not error signals.
- In TUI mode, use `ErrorDialog(title, message, detail, fatal)` for errors the user must acknowledge.
  - `fatal=True`: config/setup errors → app exits after OK.
  - `fatal=False`: transient errors (network, transcription) → app continues.
- In CLI mode, use `console.print()` for warnings/errors.
- In `core.py` library functions, let exceptions propagate to callers who decide the UI treatment.
- Windows-only DLL path additions (`os.add_dll_directory`) are exempt — they are expected failures on non-Windows.

## Config
- The config file is TOML (`~/.config/aitranscribe/config.toml`, schema `version = 2`) and lives in `config.py`; `main.py` never parses it directly. All schema, key resolution, migration and writing logic belongs in `config.py`.
- **A scope table (`[stt]`, `[llm]`) holds the selector only** (`provider = "<profile>"`). Everything about an endpoint — `base_url`, keys, model, chunk limits — lives in `[<scope>.providers.<name>]`. Never add a scope-level override for a profile field (the old `STT_MODEL` override is gone on purpose): a second value for the same thing is how the dotenv file became unmaintainable. Ad-hoc overrides are CLI flags (`--stt-model`).
- **One value, one place.** The model belongs to the profile, so switching providers switches the model with it. New settings that describe an endpoint go into the profile table.
- **STT and LLM never share credentials.** Build each client from its own `Endpoint` via `_build_client()`; do not reintroduce a shared `GROQ_API_KEY`-style variable that serves both scopes.
- **Chunk ceilings are per profile** (`max_upload_s`, `max_upload_mb`). `chunk_audio()` is called through `main._chunk_with_active_profile()`; never reintroduce a global `GROQ_MAX_UPLOAD_S` for the upload path (Groq needs 120 s, self-hosted endpoints do not).
- Unknown `provider` values are a hard `ConfigError` listing available profiles. No silent fallback to a default provider.
- Writes go through `config.set_value()` (tomlkit), which preserves comments and layout; never `json`/`toml`-dump the whole document for a single setting.
- Migration is one-way and one-shot: `config.migrate_if_needed()` only runs when `config.toml` is missing, writes the TOML file, and moves the legacy file to `aitranscribe.conf.bak-<timestamp>`. Never resurrect append-on-start migrations.
- TUI inputs (`PersistInput`) persist to config on blur or Enter (submit), never per keystroke; `Input.Changed` only marks inputs dirty.
- Provider switches persist only `[<scope>].provider`; the model input is refilled from the new profile and the auto-refill must not be persisted as a model edit (`_dirty_inputs.discard`).
- `typer.Exit` inherits from `Exception` — never wrap CLI exit-raising blocks in `except Exception`; catch the specific error type (e.g. `sqlite3.Error`).

## Testing
- Cover TUI integration points from the CLI layer with focused unit tests instead of trying to run an interactive terminal session in `pytest`.
- **Tests never touch `~/.config/aitranscribe`.** `tests/conftest.py` owns the isolation of `main.CONFIG_DIR` and its derived paths; a test that needs a different config file patches `main.CONFIG_FILE`/`main.PROMPTS_CONFIG` with `monkeypatch` inside `tmp_path`.
- Structural changes to `prompts.toml` (new tables) must be seeded by `_seed_missing_prompt_keys()`; value-only default changes must extend the `_LEGACY_*` upgrade path. Both paths need a test in `tests/test_cli.py` (`test_load_prompts_*`).
- Add focused unit tests for clipboard fallback helpers and TUI state-selection behavior instead of trying to verify them through live terminal automation.
- `core.py` tests live in `tests/test_core.py` (all core functions in one file); mock `core.subprocess.run` or `core._ffmpeg` and use pytest `tmp_path` for real files — never mock `os.path` for `chunk_audio` discovery logic.
- When a tested function closes a file handle before you can assert on it (e.g. `transcribe_audio`), capture content via a `side_effect` function instead of asserting on the call-args file object later.
