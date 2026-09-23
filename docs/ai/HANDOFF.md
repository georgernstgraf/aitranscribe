# Handoff

No pending implementation tasks. As of 2026-09-23 both community PRs are merged to main:

## 2026-09-23 session: merge AlphaVIE PRs #76 and #77
- PR #76 (quoted file paths): `normalize_file_path()` strips one matching outer quote pair before TUI and CLI file processing; `transcribe_file` and `process_file_for_tui` both normalize. Merged as bfc3e05.
- PR #77 (large media / FFmpeg on Windows): `_ffmpeg`/`_ffprobe` turn `FileNotFoundError` into actionable install messages; `compress_audio` extracts the first audio stream (`-map 0:a:0 -vn`); new `prepare_file_for_transcription()` converts >25 MB inputs to 32 kbps MP3 before duration-based chunking (shared by TUI + CLI); `chunk_audio` uses `ceil` for the duration-derived segment so no tiny trailing chunk is produced. Conflicts against #76 in `main.py` and `docs/ai/*` resolved by keeping both changes (normalize then prepare in `process_file_for_tui`).
- Verification: PR #76 branch 160 passed / 1 skipped; PR #77 branch 163 passed / 1 skipped; merged main suite re-run.

## 2026-09-21 session: repo hygiene dirt cleanup (#74, pushed as e6ea800)
- `skills/` symlink removed (was a link into opencode-helpers, not a copy); stale skills/ mandates in PITFALLS/DECISIONS updated to global skill resolution.
- Staged AGENTS.md lean rewrite committed (was already the effective instructions).
- Stale 4-line tui.py select/refresh tweak reverted (origin TUI is far newer).
- Incident: `rm -rf skills/` with trailing slash emptied the helper repo's skills first — fully recovered via `git checkout`, nothing pushed there. Pitfall recorded.
- Tree fully clean. Issue #74 CLOSED per owner.

## 2026-09-21 session: prompt transplant from polished-recognition (#73 CLOSED, pushed as 58b1301)
- `[post_process.translate]` default hardened to the sister project's #56 clause; `[post_process.system]` gains the injection-guard line (restores pre-port core.py protection).
- `_load_prompts()` auto-upgrades pristine legacy values (full-pristine files rewritten, customized files upgraded in memory with notice); 5 new tests in tests/test_cli.py, 2 expectations updated.
- Verification: full suite on fresh venv under `xvfb-run`: 156 passed, 1 skipped, 1 failed (`test_cli_file_missing_arg`, pre-existing/environmental — needs valid GROQ_API_KEY in real config; fails identically on unmodified baseline). Issue #73 CLOSED per owner.

## 2026-09-19 session: duration-based chunking (pushed as 5d1af8a/24cff9f)
- Partial-transcription bug (43-min/24 MB Zoom m4a truncated mid-sentence by Groq STT single upload) fixed: `chunk_audio` also splits by duration (`max_duration_s=600`, segment_time = min(size-derived, duration-derived), 60s floor).
- Raw-mode trust: proof tests that filesystem-file raw bypasses the LLM; pipeline reports `post_process: skipped` in raw mode.
- Verified end-to-end: 6 chunks, complete raw transcript (ID 2012, 19.515 chars, true last words).

Last cleared: 2026-09-23.
