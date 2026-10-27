# Handoff

## 2026-10-27 session: TOML config schema v2, provider profiles (#86)
- Shipped: `config.toml` (schema `version = 2`) replaces `aitranscribe.conf`.
  Scope tables hold the selector only; `[<scope>.providers.<name>]` carries
  `base_url`, `api_key`/`api_key_env` (string or array), `model`, and its own
  `max_upload_s`/`max_upload_mb`.
- New `config.py` (load/validate/key-resolution/render/write/migrate),
  `config.example.toml`, `tests/test_config.py`.
- New CLI: `aitranscribe config show|check [--probe]|edit|migrate|path`.
- TUI: STT/LLM provider selectors; the model input follows the selected
  profile and is not persisted as a model edit.
- Owner's live config is migrated and switched to
  `[stt].provider = "selfhosted-1"` (Whisper `large-v3` on gregor via
  `https://whisper.kik.spengergasse.at/v1`, 900 s / 100 MB) with
  `[llm].provider = "groq"` (`openai/gpt-oss-120b`). Legacy dotenv file kept as
  `~/.config/aitranscribe/aitranscribe.conf.bak-20261027-071647`.
- Verified: 254 tests pass; `config check --probe` green for both scopes;
  live run transcribes through gregor and post-processes through Groq.
- No pending implementation tasks for #86.

## Notes for the next agent
- Never add a scope-level override (e.g. `[stt].model`): one value, one place —
  the profile owns its model. Ad-hoc overrides are CLI flags.
- `console.print` needs `markup=False` for anything containing `[stt]`-style
  text, otherwise Rich eats the brackets.
- `main.get_tui_settings()` reloads from `CONFIG_FILE`; tests only need to
  patch `main.CONFIG_FILE`, not the `CONFIG` global.
- `python-dotenv` is migration-only now (one release of grace, then remove).
- `docs/ai/DECISIONS.md` (249 lines) should be split by topic next touch.
- Host has no `Xvfb`/`xvfb-run`; headless pytest works with
  `PYNPUT_BACKEND=dummy`.

Last cleared: 2026-10-27.
