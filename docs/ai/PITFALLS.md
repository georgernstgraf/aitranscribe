# Pitfalls

Things that do not work, subtle bugs, and non-obvious constraints.
Read this file carefully before making changes in affected areas.

- Do not pass Markdown backticks unescaped inside `gh issue create --body "..."`; the shell will treat them as command substitution.
- `runner.invoke(app, [])` does not preserve a reliable `sys.argv` shape for default-mode detection, so default TUI launch logic must be inferred from parsed option values instead.
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
