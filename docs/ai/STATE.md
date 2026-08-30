# Project State

Current status as of 2026-08-30.

## Current Focus
Audit issue #63 is now fully remediated. Final items closed this session: #8 (`chunk_audio` size-aware segmentation — segment length derived from bitrate via ffprobe duration, 5% margin, 60s floor) and #9 (`compress_audio` verifies non-empty output; `transcribe_audio` raises `FileNotFoundError` for missing files). 138 tests pass.

## Completed (this cycle)
- [x] core.py #8/#9: chunk_audio computes `-segment_time` from max_size_mb/duration instead of fixed 600s; compress_audio output verification; transcribe_audio file-existence guard; 6 new tests + 3 updated in test_core.py (21 core tests, 138 total pass)
- [x] TUI launch behavior: starts in Command Mode (AUTO_FOCUS=None, _focus_initial_widget removed), recording mode always starts microphone (TRANSCRIBE_SOURCE removed from config/code/docs), startup summary backfill no longer leaves [x] tick (success → pending, errors still visible); 132 tests pass
- [x] Config file renamed to `aitranscribe.conf` (main.py CONFIG_FILE, test fixtures, README, config.example); user's file renamed on disk, keys verified intact; no auto-migration (manual rename required for other users)
- [x] TUI cleanup-mode label changed to "Cleanup Only" (mode key `cleanup` unchanged)
- [x] Prompt port from ../polished-recognition (prompts.json → _DEFAULT_PROMPTS_TOML; build_post_process_messages gains source_language param; _validate_prompts requires post_process.system.prompt)
- [x] core.transcribe_audio switched to verbose_json, returns tuple (text, language); run_transcription_pipeline passes first known chunk language to build_post_process_messages
- [x] Prior cycle: #63 audit remediation (#62/#67–#72) complete and user-verified

## Pending
- None open

## Blockers
- None

## Next Session Suggestion
Nothing open. The #63 audit is fully closed. Optional future work: legacy CLI `transcribe_file()`/`record_from_microphone()` integration coverage (audit #18, low value).
