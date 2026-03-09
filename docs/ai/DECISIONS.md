# Decisions

Architectural and technical decisions made in this project.
Each entry documents WHAT was decided and WHY.

## 2026-03-08: Make The Terminal UI The Default Entry Point
- **Choice**: Launch the `Textual` TUI by default when `aitranscribe` is started without legacy CLI switches.
- **Reason**: The planned workflow now centers on a framed interactive terminal UI instead of a flag-driven one-shot CLI flow.
- **Considered**: Keeping the existing CLI as the default entry point.
- **Tradeoff**: The app currently supports both TUI-first behavior and legacy CLI flags, which adds transitional complexity.

## 2026-03-08: Standardize Recording On Space Toggle
- **Choice**: Use press-once / press-again space toggle recording across TUI and legacy microphone recording paths, independent of Wayland or X11.
- **Reason**: Hold-to-record proved impractical and inconsistent with the desired interaction model.
- **Considered**: Retaining push-to-talk on X11 and toggle only on Wayland.
- **Tradeoff**: Existing users of hold-to-record lose that mode entirely.

## 2026-03-08: Use Textual For The New Interface
- **Choice**: Implement the new terminal UI with `Textual` and keep transcription work off the UI thread via a worker-backed flow.
- **Reason**: The project already relies on terminal UI libraries, and `Textual` provides panels, focus handling, bindings, and async worker patterns needed for a real TUI.
- **Considered**: Expanding ad-hoc `Rich` console output into a pseudo-TUI.
- **Tradeoff**: Adds a new runtime dependency and a separate UI module to maintain.

## 2026-03-09: Keep Textual And Add Explicit Clipboard Copy
- **Choice**: Keep the `Textual` TUI and add explicit transcript copy support via `C`, using system clipboard tools first and OSC52 as a fallback.
- **Reason**: Real-world testing showed visible mouse selection inside the fullscreen TUI did not produce pasteable system clipboard content even in `kitty`, so copyability needed an app-level path.
- **Considered**: Switching terminals, relying on terminal settings, or abandoning the TUI immediately.
- **Tradeoff**: Mouse selection still is not the primary copy workflow; users need an explicit copy action.

## 2026-03-09: Replace Read Tracking With Stored Transcription History
- **Choice**: Remove `played_count`, unread counts, and mark-all-read behavior; keep all saved transcriptions as plain stored history entries.
- **Reason**: The TUI workflow now centers on browsing and previewing saved transcriptions rather than maintaining a separate unread/read state machine.
- **Considered**: Preserving unread semantics while only renaming the panel.
- **Tradeoff**: The app no longer distinguishes fresh items from older history entries.

## 2026-03-09: Persist TUI Choices And Support Filesystem Transcription In-Place
- **Choice**: Make `english` the default TUI preprocessing mode, persist TUI choices directly into `CONFIG_FILE`, and let the `Recording Mode` panel switch between microphone and filesystem-file transcription.
- **Reason**: The TUI is now the primary workflow, so it should reopen with the user's last choices and let users transcribe existing audio files without dropping to legacy CLI flags.
- **Considered**: Keeping source selection outside the TUI or treating file transcription as CLI-only.
- **Tradeoff**: The config file is updated more frequently during interactive use.

## 2026-03-09: Show Full Stored History In The TUI
- **Choice**: Populate the `Transcriptions` pane from the full database ordered by `created_at DESC` instead of limiting it to a handful of recent items.
- **Reason**: The pane is now the main browsing surface for saved transcriptions, so users need to scroll through the entire history there.
- **Considered**: Keeping the short recent-only list and relying on CLI commands for deeper history access.
- **Tradeoff**: Very large histories may make the sidebar list heavier to render.
