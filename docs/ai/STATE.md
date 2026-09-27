# Project State

Current status as of 2026-09-27.

## Current Focus
Cortecs added as a first-class LLM provider; active config now points at Cortecs `qwen3.8-flash-next`.

- `main.py` `LLM_PROVIDERS["cortecs"]`: `base_url=https://api.cortecs.ai/v1`, `env_key=CORTECS_API_KEY`, `env_model=CORTECS_LLM_MODEL`, `default_model=qwen3.8-flash-next`.
- `_create_default_config()` + `_MIGRATION_BLOCKS` include a commented Cortecs block; `config.example` and README's provider table updated.
- Active `~/.config/aitranscribe/aitranscribe.conf`: `LLM_PROVIDER="cortecs"`, `CORTECS_API_KEY` copied from opencode auth.json, `CORTECS_LLM_MODEL="qwen3.8-flash-next"`.
- Verified: provider resolves (`base_url`, model, key all load); full suite green.

## Verification
- `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q`: 186 passed, 1 skipped.
- `main.LLM_PROVIDERS["cortecs"]` + `dotenv_values(CONFIG_FILE)` sanity-checked.
- Note: no `Xvfb`/`xvfb-run` on this host; `PYNPUT_BACKEND=dummy` used instead (see HANDOFF/PITFALLS).

## Blockers
- None.

## Next Session Suggestion
- Cortecs key is a long-lived JWT from opencode auth.json; rotate if it expires.
- `DECISIONS.md` is slightly over the 200-line guide; split by topic next time it is touched.
- Pre-existing watch item from #77 still open: a small-but-long file with failing `ffprobe` is returned unsplit by `chunk_audio`.
