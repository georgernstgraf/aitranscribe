# Project State

Current status as of 2026-09-23.

## Current Focus
Both community PRs from AlphaVIE are merged to main (PR #76 as bfc3e05; PR #77 merged with a local conflict resolution on the PR branch).

- Quoted file paths: `normalize_file_path()` strips one matching outer quote pair before TUI and CLI file processing.
- Large media: filesystem inputs over 25 MB are converted directly to a 32 kbps MP3 audio stream (`compress_audio` now uses `-map 0:a:0 -vn`, shared `prepare_file_for_transcription()` for TUI + CLI) before duration-based chunking, so a 2.36 GiB MP4 mislabeled `.mp3` no longer gets copied whole or split by video bitrate.
- Missing `ffmpeg`/`ffprobe` now raise actionable install messages instead of the misleading `invalid duration (0.0s)`.
- `chunk_audio` uses `ceil` for the duration-derived segment, avoiding a tiny trailing chunk.

## Verification (on merged main)
- PR #76 branch: 160 passed, 1 skipped.
- PR #77 branch: 163 passed, 1 skipped.
- Full suite re-run on merged main (see session log).

## Blockers
- None.

## Next Session Suggestion
- Watch item from #77 review: for a small-but-long file where `ffprobe` fails, `chunk_audio` returns the file unsplit (narrow re-introduction of the truncation bug) — consider warning instead.
- Temp copies/compressed MP3s still accumulate in the system temp dir (pre-existing).
