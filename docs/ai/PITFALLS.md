# Pitfalls

Things that do not work, subtle bugs, and non-obvious constraints.
Read this file carefully before making changes in affected areas.

- **CRITICAL**: This project uses opencode-helpers skills from `skills/` directory ONLY. OpenClaw bundled skills (github, gh-issues, weather, etc.) are FORBIDDEN despite appearing in `available_skills`. Always check `skills/` first.
- Do not pass Markdown backticks unescaped inside `gh issue create --body "..."`; the shell will treat them as command substitution.
- `runner.invoke(app, [])` does not preserve a reliable `sys.argv` shape for default-mode detection, so default TUI launch logic must be inferred from parsed option values instead.
- Typer evaluates `main()` signature defaults at import time. Any option default that depends on initialized state must be `None` at import and resolved inside `main()` after `init_app()`; a direct global default (e.g. `typer.Option(GROQ_STT_MODEL, ...)`) silently bakes in `None`.
- Textual 8.x `Focus`/`Blur` events do NOT bubble — an app-level `on_blur` never fires for Input blur. To react to widget blur, subclass the widget and post a custom bubbling Message from its `on_blur` (see `PersistInput` in tui.py).
- When replacing a test function via Edit, include the next test's `def` line in BOTH oldString and newString — replacing only the `def` line deletes the following function header (happened twice with `test_wrap_text_short`).
- `typer.Exit` inherits from `Exception` (via `click.exceptions.Exit`). An `except Exception` around a block that raises `typer.Exit` converts clean exits into error exits — catch specific errors instead.
- `main.init_app()` mutates a dozen module globals. Tests calling it directly must snapshot/restore `_INIT_GLOBALS` (see `tests/test_cli.py`) or later tests fail with `KeyError` on `PROMPTS` subkeys.
- Manual testing of `main.py` default startup still requires a real terminal and microphone access; automated tests only cover the non-interactive seams.
- A fullscreen terminal UI built on the current library does not satisfy the requirement that transcript text must remain mouse-selectable for copy/paste into other applications.
- Visible mouse highlighting inside the current `Textual` TUI can still fail to populate either `PRIMARY` or `CLIPBOARD`, even when tested in `kitty`; terminal choice alone is not a reliable fix.
- Compact `Switch` widgets in the sidebar rendered badly and were not practically usable; `Checkbox` is the safer control for these boolean settings.
- Clipboard helpers may be missing from the environment; `xclip` / `wl-copy` availability materially changes whether explicit copy works without falling back to OSC52.
- TUI model and file-path inputs now persist through `Input` events, so avoid persisting empty model values and expect the config file to change during typing.
- The filesystem-file path is transcribed from the `file_path` input submission path; pressing `Space` should remain microphone-only behavior.
- A forced `height: 1` override on `Textual` `Input` widgets can break practical text entry; keep file-path entry using the default input behavior.
- When using `gh issue create` or `gh issue comment` from Bash, do not put backticks inside a double-quoted `--body`; the shell will execute them unless you use a heredoc or otherwise escape them.
- `OptionList.size.width` can be misleading on the initial TUI render; use live content-region widths with a fallback to avoid premature ellipses in history rows at startup.
- The sidebar height bug was not caused by the outer sidebar container; the real fix is to make `#history_panel` itself `1fr` and leave `Recording Mode` and `Configuration` at fixed/auto heights.
- Mouse-driven focus changes in the `Textual` TUI can leave the visible mode indicator stale unless focus-change events explicitly refresh the state field.
- Do not use the editor contents as the append base for saved transcriptions; stale pane text can diverge from the selected DB entry even when persistence still targets the correct prompt id.
- Never silently swallow exceptions with `pass` or bare `return` in `except` blocks. Every caught exception must be user-visible via `ErrorDialog` (TUI) or `console.print` (CLI). Silent failures cascade into confusing errors like `AssertionError` with no context (`main.py:753` pattern).
- `core.py`'s `compress_audio` and `chunk_audio` previously silently fell back on ffmpeg failure. They now propagate exceptions — callers must handle them explicitly. If you add a new library function that may fail due to missing system dependencies, propagate the exception rather than catching silently.
- `_DEFAULT_PROMPTS_TOML` is the source of truth for initial `prompts.toml` creation. Any structural change to the prompts file (new keys, renamed sections) must also update this embedded default string in `main.py`.
- `[post_process].system` and `[system]` are different prompts for different call sites: post-process uses `[post_process].system` (dictation-cleanup rules ending in "Return only the cleaned-up transcription"), while summary and standalone translate still use the generic `[system]` prompt. Wiring a new LLM call to the wrong one produces contradicting instructions.
- `transcribe_audio` now returns a `(text, language)` tuple from `verbose_json`, not a bare string. Existing mocks/patches of it must return tuples or unpacking in `run_transcription_pipeline` breaks.
- The config file is `~/.config/aitranscribe/aitranscribe.conf` (renamed from `config`). There is NO auto-migration: if the old `config` file still exists on an upgraded machine, the app silently creates a fresh default `aitranscribe.conf` with placeholder keys. Users must rename the old file manually.
- Textual's default `AUTO_FOCUS` focuses the first focusable widget during mount, which (a) starts the app in Pane Focus Mode and (b) fires app-level `on_descendant_focus` → `refresh_status()` before the status panel is queryable in some mount orders, crashing tests with `NoMatches: '#state_status'`. `AitranscribeTUI.AUTO_FOCUS = None` prevents both; never reintroduce automatic focus-on-mount.
- TUI tests that assert Pane-Focus-Mode status text must explicitly `set_focus(...)` a pane widget — nothing is focused at mount anymore (startup test at `test_tui.py::test_tui_starts_in_command_mode_on_mount` pins the Command Mode contract).
- When embedding TOML content in a Python triple-quoted string, avoid using `r'''\` (raw string with trailing backslash) — the backslash becomes literal and creates invalid TOML output. Use `"""\` (regular string with line-continuation backslash) instead.
- `tomllib` is stdlib in Python 3.11+ but missing in older versions. The project's pyproject.toml requires `>=3.10`, but the prompts.toml feature effectively requires 3.11+ unless a compatibility shim is added.
- In the Textual TUI, `refresh_history()` re-renders the editor via `select_history_prompt` — both directly AND indirectly through the `OptionHighlighted` event handler (setting `highlighted` after `set_options` fires the event). Any code path that must not clobber user edits (e.g. background summary completion) must use `apply_summary_to_history()` instead, which only replaces a single option's prompt text.
