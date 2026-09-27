# Handoff

No pending implementation tasks. 2026-09-27 session added the Cortecs LLM provider.

## 2026-09-27 session: Cortecs provider
- Added `cortecs` to `main.py` `LLM_PROVIDERS` (OpenAI-compatible, `https://api.cortecs.ai/v1`, default model `qwen3.8-flash-next`).
- Wired `CORTECS_API_KEY`/`CORTECS_LLM_MODEL` into `_create_default_config()`, `_MIGRATION_BLOCKS`, `config.example`, and the README provider table.
- Active conf switched to `LLM_PROVIDER="cortecs"` with the token copied from `~/.local/share/opencode/auth.json` (see DECISIONS 2026-09-27).
- Verification: `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q` → 186 passed, 1 skipped.

## Notes for the next agent
- Host has no `Xvfb`/`xvfb-run`; headless pytest works with `PYNPUT_BACKEND=dummy` (recorded in PITFALLS).
- By design, width changes do not reflow already-stored transcripts (DECISIONS 2026-09-27).

Last cleared: 2026-09-27.
