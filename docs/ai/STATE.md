# Project State

2026-10-27: Configuration is TOML now (`config.toml`, schema version 2) with
independent per-scope provider profiles. Issue #86 shipped and closed, 254
tests pass, live setup verified: STT on a self-hosted Whisper endpoint, LLM
post-processing on Groq.

## Current Focus

The dotenv config (`aitranscribe.conf`) was replaced because it could no longer
be edited: `_migrate_config()` re-appended blocks on every start (commented keys
are invisible to `dotenv_values`) — the owner's file held **118 duplicated
Cohere blocks in 511 lines** — and it could not express "STT self-hosted, LLM
cloud" at all (hardcoded Groq STT base URL, one shared `GROQ_API_KEY`).

- `config.py` (new): schema v2, `load()`, key resolution (`api_key`/
  `api_key_env`, string or array, env first), validation with profile lists in
  error messages, `set_value()` (tomlkit, comment-preserving), renderer,
  `create_default()`, one-shot dotenv migration with `.bak-<timestamp>`.
- `main.py`: globals are derived from the loaded config (`CONFIG`,
  `STT_ENDPOINT`, `LLM_ENDPOINT`, `STT_PROVIDER/LLM_PROVIDER`,
  `STT_MODEL/LLM_MODEL`); `_build_client()` keeps credentials inside their
  scope; `_chunk_with_active_profile()` passes the profile's ceilings to
  `chunk_audio`; new `aitranscribe config show|check [--probe]|edit|migrate|path`.
- `tui.py`: STT/LLM `Select`s in the Configuration panel, model follows the
  provider, provider switches persist `[<scope>].provider` only.
- `config.example.toml` replaces `config.example`; README documents the schema,
  the built-in provider defaults and the config commands.
- Owner's live `~/.config/aitranscribe/config.toml` migrated automatically on
  first start and then switched to `[stt].provider = "selfhosted-1"`
  (`https://whisper.kik.spengergasse.at/v1`, `large-v3`, 900 s/100 MB) with
  `[llm].provider = "groq"` (`openai/gpt-oss-120b`) unchanged.

## Verification

- `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q`: **254 passed**
  (21 new in `tests/test_config.py`; CLI/TUI integration for key isolation,
  provider switch, comment-preserving writes, `config show|check|migrate`).
- `aitranscribe config check --probe`: both active profiles reachable
  (selfhosted-1 → gregor via `whisper.kik.spengergasse.at`, groq → LLM).
- Live pipeline run: raw STT from gregor with umlauts intact, then Groq
  post-processing — both return the expected text.
- Headless TUI smoke (`run_test()`): provider selects show `selfhosted-1` and
  `groq`, model input prefilled `large-v3`.

## Blockers

- None.

## Next Session Suggestion

- `docs/ai/DECISIONS.md` is 249 lines (guide: 200) — split by topic next time
  it is touched (e.g. `DECISIONS-config.md`, `DECISIONS-audio.md`).
- `~/.config/aitranscribe/.aitranscribe.conf.swp` is a leftover vim swap file
  from the old dotenv config; harmless, safe to delete.
- `python-dotenv` is only used by the migration now; drop it in the release
  after next (keep `config._legacy_values` until then).
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff
  for transient 429s.
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
