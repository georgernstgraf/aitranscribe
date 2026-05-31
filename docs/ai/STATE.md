# Project State

Current status as of 2026-05-31.

## Current Focus
Eliminated all silently swallowed exceptions across the project. Modal ErrorDialog in TUI, console.print in CLI.

## Completed (this session)
- [x] Created `ErrorDialog(ModalScreen)` — centered modal with OK button, fatal/transient variants
- [x] `tui.py`: `start_recording`, `processing_failed`, `action_copy_transcript` now use ErrorDialog
- [x] `core.py`: removed silent try/except from `compress_audio` and `chunk_audio` — exceptions propagate
- [x] `main.py`: removed silent try/except from `stt_client`/`llm_client` init — exceptions propagate with clear messages
- [x] `main.py`: `pass` → `console.print` for termios setup/restore, msvcrt flush, file-copy, temp-listing
- [x] Left 4 Windows DLL paths unchanged (expected non-Windows failures, no user impact)
- [x] All 84 tests pass

## Pending
- None

## Blockers
- None

## Next Session Suggestion
Verify the ErrorDialog renders correctly in a real terminal with Textual TUI.
