# Project State

Current status as of 2026-08-30.

## Current Focus
Code audit remediation (#63) complete: #62/#67–#72 all done and closed; #63 ready to close.

## Completed (this cycle)
- [x] #71 done: shared `run_transcription_pipeline()` used by all 4 paths; tui worker closures extracted; record_from_microphone split into 5 focused helpers; PromptManager output decoupled (list_prompts returns data); RecordingController dataclass; 126 tests pass
- [x] #72 done: PromptManager exceptions propagate (ErrorDialog/console safety nets); migration ignores commented keys + single-write; TUI inputs persist on blur/submit via PersistInput; empty raw_text respected; /tmp/issue.md confirm dialog (e9a1fb6)
- [x] #67 done: terminal title set on TUI launch (OSC 2), restored in finally (f241c53)
- [x] #70 done: main.py import side-effect-free — idempotent init_app(); lazy CLI option defaults (86608eb)
- [x] #69 done: tests/test_core.py full core.py coverage (0892e80)
- [x] #68 fixed: 8 production asserts → require_stt_client()/require_llm_client() RuntimeError helpers (e153be4)
- [x] #62 fixed: summary completion no longer overwrites editor edits
- [x] #63 split into sub-issues #68–#72, all linked via Sub-Issues API; pydub → ffmpeg refactor (aa50dd9, issue #66 — closed 2026-08-30)

## Pending
- [x] User verified: legacy mic recording, live TUI recording (#71 restructure), and terminal title (#67) all work
- None open

## Blockers
- None

## Next Session Suggestion
Clean slate. Remaining audit items (#8 chunk docstring mismatch, #9 compress/transcribe error handling) were deemed optional; open fresh issues if wanted.
