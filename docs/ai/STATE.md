# Project State

2026-11-02: Live fragmentation (#88), seam conditioning (#89) and the Q-gate
(#90) shipped. Microphone recordings are cut into fragments **while
recording**, each fragment is transcribed as soon as it commits, and a seam is
conditioned (pre-roll + prompt carry-over + echo trim) only when its Q is below
`[recording].seam_quality_min` (default 10). The post-hoc `chunk_audio` path
remains only for `--file`. **340 tests pass** against a temporary config
directory.

## Current Focus

The port of polished-recognition's fragmentation into `fragmenter.py`:

- `fragmenter.py`: `evaluate()` (SilenceQuality port: 10 ms frames, 80 Hz
  one-pole high-pass without normalisation, adaptive axis `X = 0.65·mean + 100`,
  deficit-area Q, centroid cut with a 150 ms margin) and `FragmentPreparer`
  (spool + worker thread, gapless commits, `prepare_tail_sync`).
  `Fragment.silence_aligned` is a derived property (`quality > 0`).
- `main.LiveTranscriptionSession`: fragmenter → encode (`upload_format`) →
  serial transcriber thread → live partial text. `_transcribe_loop` evaluates
  the Q-gate per seam (`seam_quality = predecessor.quality`, strict
  `< seam_quality_min`) and applies pre-roll, prompt and trim only when
  conditioned. `finish()` drains the tail, writes the summary log line and
  returns the joined raw text.
- `main.process_live_recording` replaces `process_recorded_audio_for_tui`:
  validates keys, drains the session, runs the LLM post-process, encodes the
  MP3 archive (after the raw text), stores the prompt.
- `stt_log.py`: JSONL per request/error plus a stop-tap summary under
  `$XDG_STATE_HOME/aitranscribe/stt_requests.jsonl`. Request lines carry
  `quality`, `seam_quality`, `conditioned`, `prompt_chars`, `pre_roll_ms` and
  `echo_trimmed_tokens`.
- `seam.py`: `seam_prompt()` (previous transcript tail, ≤96 chars,
  word-aligned) and `trim_echo()` (≤8 tokens, head token must match, ≤1
  mismatch for k≥2; returns `(text, removed_tokens)`).
- `config.py`: `[recording]` (`cut_interval_seconds` 45, `search_window_seconds`
  5, `seam_quality_min` 10) and `upload_format` on the STT profile
  (`none` | `ogg` | `mp3`, default `none`).
- `tui.py`: `RecordingController` captures 16 kHz and streams into a sink;
  `FEEDBACK_STEPS` no longer has the `compress` stage; a `live_session_factory`
  is injected by `main.launch_tui`.
- `CONTEXT.md`: the canonical glossary (Fragmenttakt, Suchfenster, Fragment,
  Festschreibung, erzwungener Schnitt, Restfragment, Q, Naht, Q-Gate,
  konditionierte Naht, nackte Naht, Pre-roll, Prompt-Carry-over, Echo-Trim).

## Verification

- `./venv/bin/pytest -q`: **340 passed** (was 331).
- Real end-to-end against the live `selfhosted-1` profile (espeak speech →
  16 kHz → fragmenter → real STT): 5 fragments, all cuts silence-aligned, the
  262 ms tail forced; transcript complete; per-fragment STT 0.7–1.4 s.
- Full `LiveTranscriptionSession` run: 4 fragments, 4 live partial updates,
  archive MP3 written, log = 4 `stt_request` lines + 1 `stt_summary`.
- `config check --probe`: both scopes reachable.

## Blockers

- None.

## Next Session Suggestion

- Real microphone dictation on think/elite: confirm the TUI live partial text
  and measure stop→raw at the 45/5 defaults (expected: one tail upload).
  Expect naked seams and `echo_trimmed_tokens = 0` on normal dictation — that
  is the intended effect of the gate, not a regression.
- `docs/ai/DECISIONS.md` is now well over 200 lines — split by topic next touch
  (`DECISIONS-config.md`, `DECISIONS-audio.md`, `DECISIONS-prompts.md`).
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff
  for transient 429s; the live path validates API keys only after recording.
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
