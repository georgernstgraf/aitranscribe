# Project State

Current status as of 2026-08-30.

## Current Focus
Issue remediation: #62 fixed and closed; #63 audit split into 5 linked sub-issues (#68–#72) for future sessions.

## Completed (this cycle)
- [x] #62 fixed: summary completion no longer overwrites editor edits — new `apply_summary_to_history()` in tui.py updates a single history option via `replace_option_prompt`; summary worker uses it instead of `refresh_history()`; `_history_option_label()` extracted
- [x] 3 regression tests added (slow-summary edit preservation, targeted update, unknown-id no-op); 88 tests pass
- [x] Committed c73021e `fix: summary completion no longer overwrites editor edits (#62)`, pushed, #62 commented and closed
- [x] #63 split into sub-issues #68 (asserts/LLM guard), #69 (core.py tests), #70 (import side effects), #71 (pipeline dedup), #72 (config/state robustness) — all linked to #63 via Sub-Issues API; plan comment posted on #63
- [x] pydub → ffmpeg refactor committed earlier this session (aa50dd9, issue #66)

## Pending
- [ ] #68 Replace production asserts with typed errors + guard LLM response access
- [ ] #69 Add core.py test coverage
- [ ] #70 Move module-level side effects out of main.py import
- [ ] #71 Deduplicate audio pipeline logic
- [ ] #72 Config and state robustness (migration, debounce, truthy checks, typing)
- [ ] #67 (new, untriaged): Set Linux terminal title to current app name
- [ ] docs/ai/ knowledge files (STATE/DECISIONS/PITFALLS edits) are modified but uncommitted

## Blockers
- None

## Next Session Suggestion
Start with #68 (quick win), then #69. Close #63 only after all sub-issues are closed (never close a parent with open sub-issues).
