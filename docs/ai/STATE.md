# Project State

Current status as of 2026-08-30.

## Current Focus
Issue remediation: #62/#67/#68/#69/#70/#72 done and closed; #63 sub-issue #71 remaining.

## Completed (this cycle)
- [x] #72 done: PromptManager exceptions propagate (ErrorDialog/console safety nets); migration ignores commented keys + single-write; TUI inputs persist on blur/submit via PersistInput; empty raw_text respected; /tmp/issue.md confirm dialog; clipboard Mapping typing unified; 8 new tests; 122 pass
- [x] #67 done: terminal title set on TUI launch (OSC 2, query-previous via termios raw read), restored in finally; 5 tests; f241c53
- [x] #70 done: main.py import side-effect-free — idempotent init_app(); lazy CLI option defaults; 3 tests (86608eb)
- [x] #69 done: tests/test_core.py full core.py coverage (0892e80)
- [x] #68 fixed: 8 production asserts → require_stt_client()/require_llm_client() RuntimeError helpers; core.process_with_llm() zero-choices guard (e153be4)
- [x] #62 fixed: summary completion no longer overwrites editor edits (earlier this cycle)
- [x] #63 split into sub-issues #68–#72, all linked to #63 via Sub-Issues API
- [x] pydub → ffmpeg refactor committed earlier this session (aa50dd9, issue #66)

## Pending
- [ ] #71 Deduplicate audio pipeline logic (last sub-issue before closing #63)

## Blockers
- None

## Next Session Suggestion
#71 pipeline dedup, then verify all #63 sub-issues closed and close #63 with summary comment.
