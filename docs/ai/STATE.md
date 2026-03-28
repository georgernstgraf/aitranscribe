# Project State

Current status as of 2026-03-28.

## Current Focus
Auto-return to command mode implemented. Ready for manual validation in real terminal.

## Completed (this session)
- [x] Auto-return to command mode after clicks in pane focus mode (issue #61)
  - Transcriptions pane: select → command mode
  - Recording Mode → Microphone: select → command mode
  - Recording Mode → Filesystem file: select → pane mode (for path entry)
  - Preprocess modes (Raw/Cleanup/English): select → command mode

## Completed (previous cycle)
- [x] Add 'D' key to translate active transcript to German via OpenRouter LLM
- [x] Add 'E' key to translate active transcript to English via OpenRouter LLM
- [x] Wire translate_text callback through TUI initialization
- [x] Fix SQLite journal mode to DELETE for cloud sync compatibility (OneDrive, Dropbox, etc.)
- [x] Add skill source PRE-CHECK section to AGENTS.md to prevent OpenClaw bundled skill usage

## Pending
- [ ] Manually validate the TUI workflow in a real terminal with microphone access.
- [ ] Manually validate the new translation shortcuts (D, E) in a real TUI session.
- [ ] Manually validate the new filesystem-file transcription flow and live config persistence in a real terminal session.
- [ ] Manually validate startup summary backfill and post-transcription background summary refresh in a real TUI session.
- [ ] Manually validate auto-return to command mode behavior in pane focus mode.
- [ ] Decide which remaining CLI switches should be fully replaced versus retained as compatibility paths.
- [ ] Decide whether native mouse-based transcript selection still needs a stronger solution beyond the new explicit `C` copy workflow.
- [ ] Polish the TUI configuration surface and overall layout based on manual validation results.

## Blockers
- None

## Next Session Suggestion
Start with a real-terminal TUI launch to validate auto-return to command mode behavior, then continue with remaining manual validation passes.