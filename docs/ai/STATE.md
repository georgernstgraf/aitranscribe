# Project State

Current status as of 2026-08-30.

## Current Focus
polished-recognition prompt port complete (uncommitted at session end): new `[post_process].system` prompt with `{{source_language_clause}}`/`{{target_language_clause}}`, bare `{{text}}` user template, STT now returns `(text, language)` via `verbose_json` and threads detected language into post-process messages. 130 tests pass. User's `~/.config/aitranscribe/prompts.toml` deleted and regenerated from new defaults.

## Completed (this cycle)
- [x] TUI launch behavior: starts in Command Mode (AUTO_FOCUS=None, _focus_initial_widget removed), recording mode always starts microphone (TRANSCRIBE_SOURCE removed from config/code/docs), startup summary backfill no longer leaves [x] tick (success → pending, errors still visible); 132 tests pass
- [x] Config file renamed to `aitranscribe.conf` (main.py CONFIG_FILE, test fixtures, README, config.example); user's file renamed on disk, keys verified intact; no auto-migration (manual rename required for other users)
- [x] TUI cleanup-mode label changed to "Cleanup Only" (mode key `cleanup` unchanged)
- [x] Prompt port from ../polished-recognition (prompts.json → _DEFAULT_PROMPTS_TOML; build_post_process_messages gains source_language param; _validate_prompts requires post_process.system.prompt)
- [x] core.transcribe_audio switched to verbose_json, returns tuple (text, language); run_transcription_pipeline passes first known chunk language to build_post_process_messages
- [x] Tests updated: prompt-builder clause cases, pipeline language threading, verbose_json response_format; 130 pass
- [x] Prior cycle: #63 audit remediation (#62/#67–#72) complete and user-verified

## Pending
- None open

## Blockers
- None

## Next Session Suggestion
Commit the prompt-port changes if not yet committed. Remaining audit items (#8 chunk docstring mismatch, #9 compress/transcribe error handling) remain optional.
