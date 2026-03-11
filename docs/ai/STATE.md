# Project State

Current status as of 2026-03-11.

## Current Focus
Keep the TUI naming and docs aligned while the remaining work stays on manual real-terminal validation.

## Completed (this cycle)
- [x] Renamed the `english` Recording Mode option to `Cleanup + Translate to English` in the shared preprocessing-mode mapping and the TUI radio buttons.
- [x] Renamed the `cleanup` Recording Mode option to `Cleanup Text / Preserve Language` in the shared preprocessing-mode mapping and the TUI radio buttons.
- [x] Updated README wording so TUI preprocessing mode descriptions and the direct-English example heading match the new labels.

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
Start with a real-terminal TUI launch to confirm the renamed preprocessing labels read well in the sidebar, then continue the remaining manual validation passes.
