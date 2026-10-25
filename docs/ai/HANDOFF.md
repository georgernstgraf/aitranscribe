# Handoff

## 2026-10-25 session: no-audio input freeze fix (#84)
- Symptom: after an Ubuntu upgrade, the second `Space` did not stop the
  recording — the TUI stayed on `Recording` for up to 25 s and then only said
  "No audio recorded". Cause: the OBSBOT webcam mic became the PipeWire default
  source, delivered 0 callbacks at 44.1 kHz, and `stream.stop()` blocked inside
  the Textual event loop. Full measurements in `docs/ai/PITFALLS.md`.
- Fix (commit 03b95b2): `_close_stream_bounded()` + `STREAM_STOP_TIMEOUT_S`,
  `RecordingController.frames_captured`/`device_label()`, TUI watchdog
  (`schedule_audio_probe` → `check_audio_input` → `report_no_audio_input` with
  a `No Audio Input` dialog), device name in the zero-audio messages, README
  troubleshooting section.
- Verified: 215 tests pass; live broken source aborts after 7 s with the dialog;
  live healthy source records 197k frames without a false alarm.
- User-side workaround (already applied by the owner): set the Ubuntu sound
  input to the internal/external mic instead of the webcam.
- No pending implementation tasks.

## Notes for the next agent
- Host has no `Xvfb`/`xvfb-run`; headless pytest works with `PYNPUT_BACKEND=dummy`.
- Audio diagnostics on think: `./venv/bin/python -c "import sounddevice as sd;
  print(sd.query_devices(kind='input'))"` plus a 2 s `InputStream` probe that
  counts callbacks — a source that returns 0 callbacks is the failure mode above.
- `P` and `Escape` are Command-Mode hotkeys; `Space` stops an active recording
  only while nothing is focused (Pane Focus Mode types instead).
- By design, width changes do not reflow already-stored transcripts (DECISIONS 2026-09-27).

Last cleared: 2026-10-25.
