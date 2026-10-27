# History

Append-only archive of superseded knowledge entries. Newer entries at the bottom.
Format: `## YYYY-MM-DD (SUPERSEDED YYYY-MM-DD, origin: <FILE>, reason: <why or #NNN>): <Title>`

## 2026-10-27 (SUPERSEDED 2026-10-27, origin: PITFALLS.md, reason: tests are config-isolated now, see tests/conftest.py)
### `test_cli_file_missing_arg` depends on the real config
`test_cli_file_missing_arg` depends on a valid `GROQ_API_KEY` in the real
`~/.config/aitranscribe/aitranscribe.conf` (the autouse `init_app` fixture loads real config,
and key validation runs before the file check). On hosts without keys it fails with
"GROQ_API_KEY is not set" instead of "File not found" — pre-existing environmental failure,
unrelated to prompt changes (verified identical on unmodified baseline).

## 2026-10-27 (SUPERSEDED 2026-10-27, origin: PITFALLS.md, reason: `_seed_missing_prompt_keys()` repairs structural gaps in place)
### A structural `_DEFAULT_PROMPTS_TOML` change requires manual `prompts.toml` edits
When `_DEFAULT_PROMPTS_TOML` changes structurally (e.g. new `[post_process.system]`), an
existing user `prompts.toml` must be updated manually — `_validate_prompts` then exits with
`SystemExit(1)` on EVERY CLI invocation AND breaks the entire test suite at collection (test
fixtures load the user's real config). Symptom: dozens of `ERROR tests/...::test_x` fixtures
with "Missing required prompt key".

## 2026-10-27 (SUPERSEDED 2026-10-27, origin: PITFALLS.md, reason: `pyproject.toml` now requires `>=3.11`)
### `tomllib` availability vs the 3.10 floor
`tomllib` is stdlib in Python 3.11+ but missing in older versions. The project's
pyproject.toml previously declared `>=3.10`, so the prompts.toml feature effectively required
3.11+ unless a compatibility shim was added. Since schema v2 the floor is `>=3.11`.

## 2026-10-27 (SUPERSEDED 2026-10-27, origin: CONVENTIONS.md, reason: `{{translate}}` is no longer a user-template placeholder)
### `{{translate}}` sub-template resolution
The translation sub-template (`{{translate}}` in the post_process user template) is resolved
before injection — when no translation is requested, the placeholder is replaced with an empty
string, keeping exactly 2 messages to the LLM. This described the pre-#73 template shape.
Since #73 the translation clause travels in the system prompt
(`{{target_language_clause}}`) and `build_post_process_messages` substitutes only
`{{text}}` in the user template, so a `{{translate}}` left in a customized template reaches
the model verbatim.
