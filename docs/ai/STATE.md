# Project State

Current status as of 2026-03-09.

## Current Focus
Move AI Transcribe from a CLI-first recorder to a TUI-first transcription workflow.

## Completed (this cycle)
- [x] Added a new `Textual` TUI with framed status, transcript, feedback, configuration, and unread-history panels.
- [x] Made no-argument startup launch the TUI by default while preserving legacy CLI flows when switches are supplied.
- [x] Standardized microphone recording on space-to-start / space-to-stop toggle behavior.
- [x] Added queue support for unread counts, recent unread items, and marking all stored transcriptions as read.
- [x] Added regression tests for default TUI launch, preprocessing mode mapping, and mark-all-read behavior.
- [x] Tightened the TUI layout to use horizontal space better and reduce excessive vertical spacing.
- [x] Added explicit transcript copy support with system clipboard helpers and OSC52 fallback, plus installed `xclip` and `wl-clipboard` in the environment.
- [x] Replaced broken sidebar `Switch` controls with usable `Checkbox` controls.
- [x] Made unread transcription previews keyboard-navigable and wired the selected entry to show its full text in the transcript panel.

## Pending
- [ ] Manually validate the TUI workflow in a real terminal with microphone access.
- [ ] Decide which remaining CLI switches should be fully replaced versus retained as compatibility paths.
- [ ] Decide whether native mouse-based transcript selection still needs a stronger solution beyond the new explicit `C` copy workflow.
- [ ] Polish the TUI configuration surface and overall layout based on manual validation results.

## Blockers
- None

## Next Session Suggestion
Start with issue #42, manually test the improved clipboard and unread-preview flows, then choose the next slice of TUI polish versus CLI retirement.
