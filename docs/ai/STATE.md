# Project State

Current status as of 2026-03-09.

## Current Focus
Move AI Transcribe from a CLI-first recorder to a TUI-first transcription workflow.

## Completed (this cycle)
- [x] Added a new `Textual` TUI with framed status, transcript, feedback, configuration, and unread-history panels.
- [x] Made no-argument startup launch the TUI by default while preserving legacy CLI flows when switches are supplied.
- [x] Standardized microphone recording on space-to-start / space-to-stop toggle behavior.
- [x] Replaced unread/read queue state with plain stored transcription history and migrated old `played_count` databases in place.
- [x] Added regression tests for default TUI launch, preprocessing mode mapping, prompt deletion behavior, and three-digit temp recording versions.
- [x] Tightened the TUI layout to use horizontal space better and reduce excessive vertical spacing.
- [x] Added explicit transcript copy support with system clipboard helpers and OSC52 fallback, plus installed `xclip` and `wl-clipboard` in the environment.
- [x] Replaced broken sidebar `Switch` controls with usable `Checkbox` controls.
- [x] Made stored transcription previews keyboard-navigable on entry and wired the selected entry to show its full text in the transcript panel.
- [x] Made `english` the default TUI preprocessing mode and persisted TUI choices directly into config.
- [x] Added filesystem audio transcription to the TUI `Recording Mode` panel and kept queue storage always on.
- [x] Removed application-managed temp cleanup and switched temp recording copies to three-digit suffixes like `v001`.
- [x] Made the `Transcriptions` pane scroll through the full stored history in newest-first order.
- [x] Restored direct typing in the TUI `File` input and documented the `xclip` / `wl-clipboard` clipboard helpers in `README.md`.

## Pending
- [ ] Manually validate the TUI workflow in a real terminal with microphone access.
- [ ] Manually validate the new filesystem-file transcription flow and live config persistence in a real terminal session.
- [ ] Decide which remaining CLI switches should be fully replaced versus retained as compatibility paths.
- [ ] Decide whether native mouse-based transcript selection still needs a stronger solution beyond the new explicit `C` copy workflow.
- [ ] Polish the TUI configuration surface and overall layout based on manual validation results.

## Blockers
- None

## Next Session Suggestion
Start with manual validation of microphone and filesystem-file TUI flows, then choose the next slice of TUI polish versus CLI retirement.
