# Project State

Current status as of 2026-08-30.

## Current Focus
Issue remediation: #62/#68 fixed and closed; #63 audit sub-issues #69–#72 remaining; #69 done.

## Completed (this cycle)
- [x] #69 done: new `tests/test_core.py` (14 tests) covering `_ffmpeg`/`_ffprobe` (success/failure), `get_audio_duration`, `compress_audio` (naming/args), `chunk_audio` (passthrough/segment args/discovery/fallback), `transcribe_audio` (mocked client); 3 `process_with_llm` tests moved from test_cli.py to test_core.py; 106 tests pass
- [x] #68 fixed: 8 production asserts → `require_stt_client()`/`require_llm_client()` RuntimeError helpers; `core.process_with_llm()` zero-choices guard (e153be4)
- [x] #62 fixed: summary completion no longer overwrites editor edits (earlier this cycle)
- [x] #63 split into sub-issues #68–#72, all linked to #63 via Sub-Issues API
- [x] pydub → ffmpeg refactor committed earlier this session (aa50dd9, issue #66)

## Pending
- [ ] #70 Move module-level side effects out of main.py import
- [ ] #71 Deduplicate audio pipeline logic
- [ ] #72 Config and state robustness (migration, debounce, truthy checks, typing)
- [ ] #67 (new, untriaged): Set Linux terminal title to current app name

## Blockers
- None

## Next Session Suggestion
Start with #70 (unblocks test refactors), then #71, #72. Close #63 only after all sub-issues are closed (never close a parent with open sub-issues).
