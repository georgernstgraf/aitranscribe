# Project State

Current status as of 2026-08-30.

## Current Focus
Issue remediation: #62 fixed and closed; #63 audit split into 5 linked sub-issues (#68–#72); #68 done, working through the rest.

## Completed (this cycle)
- [x] #68 fixed: all 8 production `assert stt_client/llm_client is not None` replaced with `require_stt_client()` / `require_llm_client()` helpers raising `RuntimeError` with user-facing messages; `stt_missing_message()` / `llm_missing_message()` are the single message source, reused by `validate_api_keys()`; `core.process_with_llm()` raises `RuntimeError` on zero choices and handles `None` content; 7 new tests, 95 pass
- [x] #62 fixed: summary completion no longer overwrites editor edits (earlier this cycle)
- [x] #63 split into sub-issues #68–#72, all linked to #63 via Sub-Issues API
- [x] pydub → ffmpeg refactor committed earlier this session (aa50dd9, issue #66)

## Pending
- [ ] #69 Add core.py test coverage
- [ ] #70 Move module-level side effects out of main.py import
- [ ] #71 Deduplicate audio pipeline logic
- [ ] #72 Config and state robustness (migration, debounce, truthy checks, typing)
- [ ] #67 (new, untriaged): Set Linux terminal title to current app name

## Blockers
- None

## Next Session Suggestion
Start with #69 (quick win, pairs with #71), then #70, #72. Close #63 only after all sub-issues are closed (never close a parent with open sub-issues).
