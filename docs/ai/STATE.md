# Project State

Current status as of 2026-03-27.

## Current Focus
SQLite journal mode fix merged; AGENTS.md pre-check for skills added. Ready for next TUI validation session.

## Completed (this session)
- [x] Fix SQLite journal mode to DELETE for cloud sync compatibility (OneDrive, Dropbox, etc.)
- [x] Add skill source PRE-CHECK section to AGENTS.md to prevent OpenClaw bundled skill usage

## Pending
- [ ] Manually validate the TUI workflow in a real terminal with microphone access.
- [ ] Manually validate the new filesystem-file transcription flow and live config persistence in a real terminal session.
- [ ] Manually validate startup summary backfill and post-transcription background summary refresh in a real TUI session.
- [ ] Decide which remaining CLI switches should be fully replaced versus retained as compatibility paths.
- [ ] Decide whether native mouse-based transcript selection still needs a stronger solution beyond the new explicit `C` copy workflow.
- [ ] Polish the TUI configuration surface and overall layout based on manual validation results.

## Blockers
- None

## Next Session Suggestion
Start with a real-terminal TUI launch to validate the append mode fix and refined modal state/flash feedback behavior with real mouse and microphone interaction, then continue the remaining manual validation passes.