# Project State

Current status as of 2026-06-11.

## Current Focus
Moved all LLM prompts from hardcoded Python strings to a configurable `~/.config/aitranscribe/prompts.toml` file (TOML format, auto-created from embedded defaults).

## Completed (this cycle)
- [x] `core.py`: `process_with_llm` now accepts pre-built `messages: list[dict]` — no internal prompt construction
- [x] `main.py`: Removed `PRE_PROCESS_MODES`, `SUMMARY_PROMPT`, `TRANSLATE_TO_*_PROMPT` constants
- [x] `main.py`: Added TOML loading (`_load_prompts`, `_validate_prompts`), auto-create from embedded defaults, 3 message builders (`build_post_process_messages`, `build_summary_messages`, `build_translate_messages`)
- [x] Adopted polished-recognition prompt structure: system = constraints, user = task+data, translate as sub-template via `{{translate}}` placeholder
- [x] All 6 call sites updated to use new message builders
- [x] Tests updated: replaced 4 old prompt tests with 5 new message builder tests
- [x] All 85 tests pass

## Pending
- None

## Blockers
- None

## Next Session Suggestion
Verify prompts.toml customization works by editing the file and running the app. Consider adding a TUI settings screen for prompt editing as polished-recognition does.
