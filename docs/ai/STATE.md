# Project State

Current status as of 2026-03-11.

## Current Focus
Finish TUI layout polish so startup rendering matches the steady-state sidebar and transcript behavior.

## Completed (this cycle)
- [x] Aligned `File`, `STT-Model`, and `LLM-Model` labels vertically with their corresponding values inside the right-hand panels.
- [x] Made the `Transcriptions` pane fill the remaining sidebar height above the fixed `Recording Mode` and `Configuration` boxes.
- [x] Kept the left transcript column behavior intact while mirroring the same remaining-space principle on the right.
- [x] Fixed startup-only history truncation by scheduling an extra history refresh after the first layout pass so summaries use the same width calculation as later refreshes.
- [x] Reverted the mistaken feedback-log height expansion after confirming the four-step log still fits the original compact height.
- [x] Added regression coverage for the startup extra-refresh behavior and kept focused TUI tests green throughout the layout adjustments.

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
Start with a real-terminal TUI launch to verify the right-column height fill and startup history truncation fix together, then continue any remaining visual polish from there.
