# Project State

Current status as of 2026-03-08.

## Current Focus
Move AI Transcribe from a CLI-first recorder to a TUI-first transcription workflow.

## Completed (this cycle)
- [x] Added a new `Textual` TUI with framed status, transcript, feedback, configuration, and unread-history panels.
- [x] Made no-argument startup launch the TUI by default while preserving legacy CLI flows when switches are supplied.
- [x] Standardized microphone recording on space-to-start / space-to-stop toggle behavior.
- [x] Added queue support for unread counts, recent unread items, and marking all stored transcriptions as read.
- [x] Added regression tests for default TUI launch, preprocessing mode mapping, and mark-all-read behavior.

## Pending
- [ ] Manually validate the TUI workflow in a real terminal with microphone access.
- [ ] Decide which remaining CLI switches should be fully replaced versus retained as compatibility paths.
- [ ] Solve the mouse-copy requirement for transcript text if the current fullscreen TUI library blocks native terminal text selection.
- [ ] Polish the TUI configuration surface based on manual validation results.

## Blockers
- None

## Next Session Suggestion
Start with issue #42, run the TUI manually in a real terminal, and decide the next slice of CLI-to-TUI migration.
