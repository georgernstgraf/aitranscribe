# Handoff

## 2026-10-27 session: prompt self-healing + test isolation (follow-up to #86)
- Shipped `main._seed_missing_prompt_keys()`: a `prompts.toml` that lacks a
  required table (e.g. `[post_process.system]`, added in #73) is repaired in
  place from `_DEFAULT_PROMPTS_TOML` with tomlkit and re-read by
  `_load_prompts()`. Existing keys — including customizations — are never
  touched. `_upgrade_legacy_prompt_defaults()` keeps owning value upgrades.
- Shipped `tests/conftest.py`: the whole suite runs against a `mkdtemp()`
  config dir, so the developer's `~/.config/aitranscribe` is never read or
  written. Autouse fixture re-asserts the paths after any `importlib.reload`.
- Three new tests in `tests/test_cli.py` (seeding, customization preservation,
  isolation invariant). Full suite: 257 passed.
- Owner's live `prompts.toml` on elite was replaced with think's copy
  (md5 `75a7bbac280c3873471575381e98ca81`, default content; the previous
  customized file is at `prompts.toml.bak-2026-10-27`). It carried a
  `{{translate}}` placeholder that `build_post_process_messages()` no longer
  substitutes.
- No pending implementation tasks.

## Live config on elite (2026-10-27, after the gregor migration)
- `[stt] selfhosted-1` → `https://whisper.kik.spengergasse.at/v1`, `large-v3`,
  900 s / 100 MB (same profile as think; the API key was copied from think).
- `[llm] groq` → `openai/gpt-oss-120b` (think's setup). elite's previous
  `openrouter` profile kept a placeholder key and a deprecated model
  (`anthropic/claude-3-haiku` → 404 since 2026-09-10), so post-processing could
  not work at all before this change.
- `stt.groq`, `llm.groq`, `llm.openrouter` keys copied from think; only
  `openrouter`'s model is still stale.
- Backup: `~/.config/aitranscribe/config.toml.bak-20261027-190245`.
- Verified end to end: `config check --probe` green for both active scopes, and
  a real espeak test MP3 went gregor-STT → Groq post-process with umlauts intact.

## Notes for the next agent
- Never add a scope-level override (e.g. `[stt].model`): one value, one place —
  the profile owns its model. Ad-hoc overrides are CLI flags.
- `console.print` needs `markup=False` for anything containing `[stt]`-style
  text, otherwise Rich eats the brackets.
- `main.get_tui_settings()` reloads from `CONFIG_FILE`; tests only need to
  patch `main.CONFIG_FILE`, not the `CONFIG` global.
- Tests must go through `tests/conftest.py`'s isolated paths; do not "fix"
  `CONFIG_DIR` by adding a production env override without a decision entry.
- `python-dotenv` is migration-only now (one release of grace, then remove).
- `docs/ai/DECISIONS.md` (~260 lines) should be split by topic next touch.
- Host has no `Xvfb`/`xvfb-run`; headless pytest works with
  `PYNPUT_BACKEND=dummy` (not needed here — the suite ran without it).

Last cleared: 2026-10-27.
