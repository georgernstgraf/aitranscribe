# Project State

Current status as of 2026-03-10.

## Current Focus
Refine the TUI-first transcription workflow around saved-history browsing and LLM-generated metadata.

## Completed (this cycle)
- [x] Added a nullable `summary` column to stored transcriptions and migrated existing SQLite databases in place.
- [x] Backfilled missing transcription summaries during TUI/default startup using the existing LLM post-processing client.
- [x] Kept new transcript display fast by generating summaries for newly saved TUI transcriptions in background workers after the full transcript is shown.
- [x] Updated the `Transcriptions` pane to display stored summaries instead of leading transcript words when summaries exist.
- [x] Added regression tests for summary migration, summary backfill/update behavior, and TUI summary rendering/background generation.

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
Start with real-terminal validation of summary backfill and background summary refresh, then continue TUI polish based on what that session reveals.
