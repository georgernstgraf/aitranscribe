# Handoff

No pending tasks. All session work committed and pushed to main:

- polished-recognition prompt port: `[post_process].system` with `{{source_language_clause}}`/`{{target_language_clause}}`, bare `{{text}}` user template, verbose_json STT language detection threaded into post-process messages
- Config file renamed to `aitranscribe.conf` (no auto-migration; user's file renamed on disk, keys verified)
- TUI cleanup-mode label now "Cleanup Only" (mode key `cleanup` unchanged)
- TUI launch: Command Mode + microphone default, no summary-backfill tick (uncommitted — push with next batch)

Last cleared: 2026-08-30.
