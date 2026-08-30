# Project State

Current status as of 2026-08-30.

## Current Focus
Issue remediation: #62/#68/#69/#70 done and closed; #63 sub-issues #71/#72 remaining.

## Completed (this cycle)
- [x] #70 done: `main.py` import side-effect-free — config create/migrate, load_dotenv, env constants, PROMPTS, OpenAI clients, PromptManager all moved into idempotent `init_app()`; `main()` calls it; stt/llm model option defaults lazy (`None` resolved post-init); autouse init fixture in test_cli.py; 3 new tests; 109 pass
- [x] #69 done: `tests/test_core.py` (14 tests) full core.py coverage; 3 process_with_llm tests moved from test_cli.py
- [x] #68 fixed: 8 production asserts → `require_stt_client()`/`require_llm_client()` RuntimeError helpers; `core.process_with_llm()` zero-choices guard (e153be4)
- [x] #62 fixed: summary completion no longer overwrites editor edits (earlier this cycle)
- [x] #63 split into sub-issues #68–#72, all linked to #63 via Sub-Issues API
- [x] pydub → ffmpeg refactor committed earlier this session (aa50dd9, issue #66)

## Pending
- [ ] #71 Deduplicate audio pipeline logic
- [ ] #72 Config and state robustness (migration, debounce, truthy checks, typing)
- [ ] #67 (new, untriaged): Set Linux terminal title to current app name

## Blockers
- None

## Next Session Suggestion
Start with #71 (pipeline dedup — #70's init_app makes DI easier now), then #72. Close #63 only after all sub-issues are closed (never close a parent with open sub-issues).
