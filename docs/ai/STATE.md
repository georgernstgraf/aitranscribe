# Project State

Current status as of 2026-03-22.

## Current Focus
TUI workflow ergonomics are improved; remaining work is manual real-terminal validation and any follow-up polish that emerges from it.

## Completed (this cycle)
- [x] Add 'a' key to append transcriptions (Space=new, 'a'=append).
- [x] Fix 'w' hotkey feedback to distinguish overwritten vs new file.
- [x] Fix save confirmation message visibility after Ctrl+S.
- [x] Name the TUI focus states explicitly as `Command Mode` and `Pane Focus Mode`.
- [x] Split the status area into separate state and flash-feedback fields.
- [x] Restore visible save/copy/write/delete confirmations in the TUI flash field.
- [x] Remove the redundant `Ctrl+Shift+C` copy binding and keep `C` as the copy hotkey.
- [x] Make append mode use the selected saved transcription as the source of truth for both rendering and persistence.
- [x] Keep the existing transcript visible immediately after pressing `A` to append.

## Previously Completed
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
Start with a real-terminal TUI launch to validate the refined modal state/flash feedback behavior and append workflow with real mouse and microphone interaction, then continue the remaining manual validation passes.
