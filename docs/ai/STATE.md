# Project State

2026-10-27: Configuration is TOML (`config.toml`, schema version 2) with
independent per-scope provider profiles (#86). Prompt migration and test
isolation were repaired the same day; **257 tests pass** against a temporary
config directory, and the owner's live setup was re-synced from think.

## Current Focus

`prompts.toml` is now self-healing and the suite is config-isolated.

- `main._seed_missing_prompt_keys()` (new): fills keys that a `prompts.toml`
  lacks entirely from `_DEFAULT_PROMPTS_TOML`, writes with tomlkit
  (comment-preserving), and `_load_prompts()` re-reads the file. Fixes the
  pre-#73 case with no `[post_process.system]` table, which used to die in
  `_validate_prompts()` with `SystemExit(1)`.
- `_upgrade_legacy_prompt_defaults()` is unchanged and still owns *value*
  upgrades; the two paths are complementary.
- `tests/conftest.py` (new): repoints `main.CONFIG_DIR`, `CONFIG_FILE`,
  `LEGACY_CONFIG_FILE`, `PROMPTS_FILE`, `PROMPTS_CONFIG` at a `mkdtemp()`
  directory at import time and again in the autouse
  `_reassert_config_isolation` fixture (needed because
  `test_import_does_not_initialize_state` reloads `main`).
- `CONVENTIONS.md` corrected: `{{translate}}` is no longer a user-template
  placeholder — the translation clause lives in the system prompt.

## Verification

- `./venv/bin/pytest -q`: **257 passed** (was 134 passed / 120 errors before
  the isolation fix; +3 new tests: `test_load_prompts_seeds_missing_system_table`,
  `test_seeding_missing_prompt_keys_preserves_customizations`,
  `test_conftest_isolates_the_suite_from_the_real_user_config`).
- Real-config safety checked by md5: a full suite run leaves
  `~/.config/aitranscribe/prompts.toml` byte-identical.
- End-to-end replay of the failure: a pre-#73 file (no `[post_process.system]`,
  custom user template) now loads, gets the table seeded, and keeps its
  customization verbatim.
- `./venv/bin/python main.py --list` runs against the live config.
- Venv: Python 3.14.4, `tomlkit` 0.15.2 installed, `pydub` gone.

## Blockers

- None.

## Next Session Suggestion

- `docs/ai/DECISIONS.md` is ~260 lines (guide: 200) — split by topic next touch
  (`DECISIONS-config.md`, `DECISIONS-audio.md`, `DECISIONS-prompts.md`).
- elite's live `config.toml` now mirrors think's active scopes: `[stt]
  selfhosted-1` (gregor `large-v3`, 900 s/100 MB) and `[llm] groq`
  (`openai/gpt-oss-120b`); both API keys were copied from think. Verified with
  a real pipeline run (espeak test MP3 → umlauts intact → Groq cleanup).
- elite's `[llm.providers.openrouter]` keeps a real key but a deprecated model
  (`anthropic/claude-3-haiku`, 404 since 2026-09-10). Retarget it (e.g.
  `anthropic/claude-haiku-4.5`) or delete the profile before switching back.
- A snapshot of the pre-change elite config is at
  `~/.config/aitranscribe/config.toml.bak-20261027-190245`.
- `~/.config/aitranscribe/.aitranscribe.conf.swp` is a leftover vim swap file
  from the old dotenv config; harmless, safe to delete.
- `python-dotenv` is only used by the migration now; drop it in the release
  after next (keep `config._legacy_values` until then).
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff
  for transient 429s.
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
