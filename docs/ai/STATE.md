# Project State

2026-11-02: Live fragmentation (#88) and seam conditioning (#89) shipped.
Microphone recordings are cut into fragments **while recording**, each fragment
is transcribed as soon as it commits, and every seam gets pre-roll, a prompt
carry-over and an echo trim. The post-hoc `chunk_audio` path remains only for
`--file`. **331 tests pass** against a temporary config directory.

## Current Focus

The port of polished-recognition's fragmentation into `fragmenter.py`:

- `fragmenter.py` (new): `evaluate()` (SilenceQuality port: 10 ms frames,
  80 Hz one-pole high-pass without normalisation, adaptive axis
  `X = 0.65·mean + 100`, deficit-area Q, centroid cut with a 150 ms margin) and
  `FragmentPreparer` (spool + worker thread, gapless commits, `prepare_tail_sync`).
- `main.LiveTranscriptionSession` (new): fragmenter → encode (`upload_format`)
  → serial transcriber thread → live partial text; `finish()` drains the tail,
  writes the summary log line and returns the joined raw text.
- `main.process_live_recording` replaces `process_recorded_audio_for_tui`:
  validates keys, drains the session, runs the LLM post-process, encodes the
  MP3 archive (after the raw text), stores the prompt.
- `stt_log.py` (new): JSONL per request/error plus a stop-tap summary under
  `$XDG_STATE_HOME/aitranscribe/stt_requests.jsonl`.
- `config.py`: `[recording]` (`cut_interval_seconds` 45, `search_window_seconds`
  5) and `upload_format` on the STT profile (`none` | `ogg` | `mp3`, default
  `none`).
- `tui.py`: `RecordingController` captures 16 kHz and streams into a sink;
  `FEEDBACK_STEPS` no longer has the `compress` stage; a `live_session_factory`
  is injected by `main.launch_tui`.
- `CONTEXT.md` (new): the canonical glossary (Fragmenttakt, Suchfenster,
  Fragment, Festschreibung, erzwungener Schnitt, Restfragment, Q, Naht,
  Pre-roll, Prompt-Carry-over, Echo-Trim).
- `seam.py` (new): `seam_prompt()` (previous transcript tail, ≤96 chars,
  word-aligned) and `trim_echo()` (≤8 tokens, head token must match, ≤1
  mismatch for k≥2). The serial transcriber composes `pre_roll + fragment` as
  one upload, sends the prompt, and trims the echo against the untrimmed
  previous transcript. A rejected prompt (HTTP 400) disables prompts for the
  session.

## Verification

- `./venv/bin/pytest -q`: **331 passed** (was 257).
- Real end-to-end against the live `selfhosted-1` profile (espeak speech →
  16 kHz → fragmenter → real STT): 5 fragments, all cuts silence-aligned, the
  262 ms tail forced; transcript complete; per-fragment STT 0.7–1.4 s.
- Full `LiveTranscriptionSession` run: 4 fragments, 4 live partial updates,
  archive MP3 written, log = 4 `stt_request` lines + 1 `stt_summary`
  (`stop_to_raw_ms` 3182 on a 3.4 s tail). Seam conditioning visible in the
  log: `pre_roll_ms=1000` and `prompt_chars` 41–54 from fragment 1 on; no
  duplicated seam words in the transcript.
- `config check --probe`: both scopes reachable.
- Live config untouched: `config.load(~/.config/aitranscribe/config.toml)`
  picks up the new defaults (`upload_format=none`, recording 45/5).

## Blockers

- None.

## Next Session Suggestion

- Real microphone dictation on think/elite: confirm the TUI live partial text
  and measure stop→raw at the 45/5 defaults (expected: one tail upload).
- #88 and #89 are both closed. A real microphone dictation is still the one
  unverified path (PortAudio), and the Q-gate for seam conditioning waits for
  data (the original's `Q < qualityMin` stitch decision).
- `docs/ai/DECISIONS.md` is now well over 200 lines — split by topic next touch
  (`DECISIONS-config.md`, `DECISIONS-audio.md`, `DECISIONS-prompts.md`).
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff
  for transient 429s; the live path validates API keys only after recording.
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
