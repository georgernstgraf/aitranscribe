# Domain Knowledge

Business rules and domain relationships not obvious from code.

## Entities
- prompt queue entry: stored transcription text plus source filename and creation timestamp; entries are plain saved history without unread/read tracking.
- transcription summary: nullable 70-80 character LLM-generated preview text stored alongside a saved transcription for history-list display.

## Rules
- LLM prompts are stored in `~/.config/aitranscribe/prompts.toml` with 5 top-level sections: `[system]` (generic constraints for summary + standalone translate), `[post_process]` (own `system` prompt ported from the polished-recognition app, plus cleanup `user` template + optional `translate` sub-template), `[summary]`, and `[translate]` (standalone).
- The `[post_process].system` prompt contains `{{source_language_clause}}` and `{{target_language_clause}}` placeholders. The source clause ("The STT service transcribed audio spoken in X.") is derived from the STT-detected language (`verbose_json`) and omitted when unknown; the target clause is the resolved `[post_process.translate]` template and omitted when no target language is set. Blank lines are collapsed to at most one and the prompt is trimmed before sending.
- The `[post_process]` user template is just `{{text}}`; all cleanup rules live in the post-process system prompt.
- All 6 required prompt keys (`system.prompt`, `post_process.system.prompt`, `post_process.user.template`, `post_process.translate.prompt`, `summary.user.template`, `translate.user.template`) must be present and non-empty in prompts.toml or the program exits with an error.
- If `prompts.toml` does not exist, it is auto-created from `_DEFAULT_PROMPTS_TOML` (embedded in `main.py`).
- The TUI transcript panel should show only the final displayed result, so when preprocessing runs the post-processed text replaces the raw transcript in the main transcript view.
- Saved transcription history includes all stored entries, and queue storage is always on for TUI-triggered transcriptions.
- The `Transcriptions` pane is the primary browser for saved history and should expose the full database in reverse chronological order.
- The `Transcriptions` pane should display stored summaries during scrolling instead of deriving previews from the first words of the full transcript whenever a summary exists.
- Summary previews in the `Transcriptions` pane should use the full visible row width and only show an ellipsis when the current rendered line cannot fit the whole text.
- The `Transcriptions` pane should occupy the remaining sidebar height above the fixed `Recording Mode` and `Configuration` boxes, mirroring how the left transcript pane fills the space between status and feedback.
- Transcript output must remain mouse-selectable so users can copy text from the terminal and paste it into other applications.
- The transcript panel doubles as a full-message preview for stored history: when the user highlights an entry with the arrow keys, that entry's complete text should replace the current idle transcript view.
- The TUI must provide an explicit transcript-copy action because visual mouse selection in the fullscreen interface is not sufficient for cross-application paste.
- The TUI `Recording Mode` panel must support both live microphone capture and filesystem audio-file transcription, with `english` as the default preprocessing mode.
- The TUI always launches in Command Mode (no focused widget) with the recording mode set to microphone; the source selection is session-only and not persisted.
- Missing summaries should be backfilled only during TUI/default startup, and newly saved TUI transcriptions should get summaries asynchronously after the full transcript is already shown.
- During live processing, the transcript pane should show raw transcription as soon as STT completes, then replace it with post-processed text once that stage finishes if post-processing is enabled.
- Startup history previews should use the same truncation result as post-transcription refreshes; the app now achieves that by rebuilding the history list once more after the first layout pass.
