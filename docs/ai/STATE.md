---
type: State
title: Project State
description: "Current project status — overwritten on every persistence run."
tags: [aitranscribe]
generated: { by: opencode/knowledge-persistence, at: 2026-11-26T08:10:00Z }
verified: { by: opencode/knowledge-persistence, at: 2026-11-26T08:10:00Z }
status: stable
sources:
  - id: issue-92
    resource: https://github.com/georgernstgraf/aitranscribe/issues/92
    title: "ESC im Pane Focus Mode bricht laufende Diktat-Aufnahme ab"
---

# Project State

2026-11-28: #94 shipped — **OpenCode Go as LLM provider**: new
`[llm.providers.opencodego]` profile (base_url
`https://opencode.ai/inference/go/openai/v1/`, default model `glm-5.3-flash`,
LLM-only in `PROVIDER_DEFAULTS`) and an automatic `x-opencode-session` header
(`_build_client`): the Go endpoint refuses requests without it (HTTP 400
`MissingSessionID`, live-verified both ways); the header goes ONLY to
host `opencode.ai` + path prefix `/inference/go/` (Console endpoint, foreign
hosts, STT untouched — mirrors polished-recognition's
`OpenCodeSessionInterceptor`). The UUID is a stable per-install id persisted at
`~/.config/aitranscribe/opencode-session-id` (0600), deliberately NOT in
`config.toml` (the TUI rewrites that file). **361 tests pass.**

## Current Focus

Live fragmentation pipeline is stable (#88/#89/#90 shipped). The 2026-11-28
session touched `main.py` (`_build_client` + two helpers), `config.py`
(PROVIDER_DEFAULTS entry) and `tests/test_cli.py` — the TUI focus/ESC path is
untouched since 2026-11-26.

## Verification

- `./venv/bin/pytest -q`: **361 passed** (was 358).
- Live smoke test against the real Go endpoint: with header → completion
  (`'OK'`), without header → HTTP 400 `MissingSessionID`.

## Blockers

- None.

## Next Session Suggestion

- Real microphone dictation on think/elite: confirm the TUI live partial text
  and measure stop→raw at the 45/5 defaults.
- `docs/ai/DECISIONS.md` is well over 200 lines — split by topic next touch
  (`DECISIONS-config.md`, `DECISIONS-audio.md`, `DECISIONS-prompts.md`).
- Pre-existing watch items: a small-but-long file with failing `ffprobe` is
  returned unsplit by `chunk_audio`; `transcribe_audio` has no retry/backoff
  for transient 429s; the live path validates API keys only after recording.
- Groq support report (mangled `text` >120 s, correct `words[]`) still owed
  upstream.
