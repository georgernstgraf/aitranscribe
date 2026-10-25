# Project State

2026-10-25: TUI recording no longer freezes when the OS default input delivers
no audio frames, and capture now uses PortAudio's native PulseAudio/PipeWire
host API instead of ALSA's `default` PCM. Issues #84 and #85 closed, 222 tests
pass.

## Current Focus
The OBSBOT webcam mic became the PipeWire default source after an Ubuntu
upgrade and delivered **zero callbacks** to `sounddevice` at 44.1 kHz, while
`stream.stop()` blocked 6.8–25 s on the Textual event loop — the TUI sat on
`Recording` and ended in a bare "No audio recorded". (Switch the system input
to another mic and everything works; that is the user's workaround.)

- `tui.py`:
  - `_close_stream_bounded()` stops/closes a PortAudio stream in a daemon thread
    with an `abort()` fallback, bounded by `STREAM_STOP_TIMEOUT_S = 1.5`.
  - `RecordingController`: `frames_captured` counter, `device_label()`,
    `last_close_stalled`, bounded `stop()`.
  - `AitranscribeTUI`: `schedule_audio_probe()` (`AUDIO_PROBE_DELAY_S = 2`) →
    `check_audio_input()` reopens the device once, then `report_no_audio_input()`
    cancels the take and shows the `No Audio Input` dialog naming the device.
  - `finish_recording()` with zero audio now names the device as well.
- `tui.resolve_input_device()` + `RecordingController.start()`: capture the
  system default source through the native `PulseAudio`/`PipeWire` host API
  (`device` index) instead of ALSA's `default` PCM — no `pa_linux_alsa.c`
  assertion spam, `stop()+close()` in 0.02 s instead of 6–25 s.
- `main._resolve_capture_device()`: same helper for the legacy CLI `record` path.
- `README.md`: new "No audio from the input device" section incl. the host-API note.

## Verification
- `PYNPUT_BACKEND=dummy ./venv/bin/pytest -q`: **222 passed** (blocked-stream
  bound, frame counter/device label, watchdog retry → dialog, no false alarm with
  frames, pause guard, device name on empty take, native host-API selection +
  fallbacks, `start()` device index, CLI helper).
- Live against the broken source (webcam via ALSA hw:1, 32 kHz): abort after
  **7 s** with the dialog, no freeze (baseline before the fix: 25 s hang).
- Live against the healthy default source via PulseAudio: 194,016 frames in
  4.5 s, `device=Default Source (PulseAudio)`, `stalled_close=False`, **0**
  ALSA assertion lines in stderr.
- Live against the broken webcam source: abort after 4.5 s with the dialog and
  0 stderr lines (before the host-API change: 25 s hang plus assertion spam).

## Blockers
- None.

## Next Session Suggestion
- `DECISIONS.md` (237 lines) still exceeds the 200-line guide; split by topic
  (e.g. `DECISIONS-tui.md`, `DECISIONS-audio.md`) next time it is touched.
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff for
  transient Groq failures (429s); charset hygiene in `main.py:80/131`
  (no `encoding="utf-8"`) and `tui.py` clipboard `subprocess` (locale encoding).
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
