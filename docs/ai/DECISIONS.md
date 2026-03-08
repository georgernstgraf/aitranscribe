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
