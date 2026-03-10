# Project State

Current status as of 2026-03-10.

## Current Focus
Polish the TUI transcription workflow so progress feedback and history previews match the actual rendered UI behavior.

## Completed (this cycle)
- [x] Replaced the old low-level feedback log with four user-facing phases: compress, transcribe, post-process, and summary.
- [x] Made the transcript pane show raw STT text as soon as transcription completes, then replace it with post-processed text when that stage finishes.
- [x] Restored the compact feedback log height to fit the new four-line phase model cleanly.
- [x] Fixed startup-only history preview truncation so summaries use the full available sidebar row width before showing ellipses.
- [x] Added regression tests for the new feedback-stage model, raw-transcript update behavior, and startup-safe history width calculation.

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
Start with a real TUI run to verify the four-phase feedback log, raw-transcript handoff, and startup history-width fix together, then continue polish from there.
