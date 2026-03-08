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
