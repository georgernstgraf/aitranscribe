# Decisions

Architectural and technical decisions made in this project.
Each entry documents WHAT was decided and WHY.

## 2026-03-08: Make The Terminal UI The Default Entry Point
- **Choice**: Launch the `Textual` TUI by default when `aitranscribe` is started without legacy CLI switches.
- **Reason**: The planned workflow now centers on a framed interactive terminal UI instead of a flag-driven one-shot CLI flow.
- **Considered**: Keeping the existing CLI as the default entry point.
- **Tradeoff**: The app currently supports both TUI-first behavior and legacy CLI flags, which adds transitional complexity.

## 2026-03-08: Standardize Recording On Space Toggle
- **Choice**: Use press-once / press-again space toggle recording across TUI and legacy microphone recording paths, independent of Wayland or X11.
- **Reason**: Hold-to-record proved impractical and inconsistent with the desired interaction model.
- **Considered**: Retaining push-to-talk on X11 and toggle only on Wayland.
- **Tradeoff**: Existing users of hold-to-record lose that mode entirely.

## 2026-03-08: Use Textual For The New Interface
- **Choice**: Implement the new terminal UI with `Textual` and keep transcription work off the UI thread via a worker-backed flow.
- **Reason**: The project already relies on terminal UI libraries, and `Textual` provides panels, focus handling, bindings, and async worker patterns needed for a real TUI.
- **Considered**: Expanding ad-hoc `Rich` console output into a pseudo-TUI.
- **Tradeoff**: Adds a new runtime dependency and a separate UI module to maintain.

## 2026-03-09: Keep Textual And Add Explicit Clipboard Copy
- **Choice**: Keep the `Textual` TUI and add explicit transcript copy support via `C`, using system clipboard tools first and OSC52 as a fallback.
- **Reason**: Real-world testing showed visible mouse selection inside the fullscreen TUI did not produce pasteable system clipboard content even in `kitty`, so copyability needed an app-level path.
- **Considered**: Switching terminals, relying on terminal settings, or abandoning the TUI immediately.
- **Tradeoff**: Mouse selection still is not the primary copy workflow; users need an explicit copy action.

## 2026-03-09: Replace Read Tracking With Stored Transcription History
- **Choice**: Remove `played_count`, unread counts, and mark-all-read behavior; keep all saved transcriptions as plain stored history entries.
- **Reason**: The TUI workflow now centers on browsing and previewing saved transcriptions rather than maintaining a separate unread/read state machine.
- **Considered**: Preserving unread semantics while only renaming the panel.
- **Tradeoff**: The app no longer distinguishes fresh items from older history entries.

## 2026-03-09: Persist TUI Choices And Support Filesystem Transcription In-Place
- **Choice**: Make `english` the default TUI preprocessing mode, persist TUI choices directly into `CONFIG_FILE`, and let the `Recording Mode` panel switch between microphone and filesystem-file transcription.
- **Reason**: The TUI is now the primary workflow, so it should reopen with the user's last choices and let users transcribe existing audio files without dropping to legacy CLI flags.
- **Considered**: Keeping source selection outside the TUI or treating file transcription as CLI-only.
- **Tradeoff**: The config file is updated more frequently during interactive use.

## 2026-03-09: Show Full Stored History In The TUI
- **Choice**: Populate the `Transcriptions` pane from the full database ordered by `created_at DESC` instead of limiting it to a handful of recent items.
- **Reason**: The pane is now the main browsing surface for saved transcriptions, so users need to scroll through the entire history there.
- **Considered**: Keeping the short recent-only list and relying on CLI commands for deeper history access.
- **Tradeoff**: Very large histories may make the sidebar list heavier to render.

## 2026-03-10: Generate Stored Transcription Summaries Asynchronously
- **Choice**: Add a nullable `summary` column to stored transcriptions, backfill missing summaries only on TUI/default startup, and generate summaries for new transcriptions in the background after the full transcript is already visible.
- **Reason**: The history pane needs concise 70-80 character previews, but the main transcription workflow should remain fast and show the full transcript without waiting for a third LLM request.
- **Considered**: Blocking startup on summary backfill, generating summaries on every CLI invocation, or waiting for summary generation before displaying new transcripts.
- **Tradeoff**: The history list can briefly show fallback transcript snippets until background summary jobs finish, and summaries remain null when LLM generation is unavailable or fails.

## 2026-03-10: Collapse Feedback Log To User-Visible Processing Phases
- **Choice**: Replace the old send/response feedback rows with four user-facing phases: compress, transcribe, post-process, and summary.
- **Reason**: Users understand workflow progress better when the log reflects meaningful stages instead of internal request boundaries, and raw STT text can appear immediately after transcription completes.
- **Considered**: Keeping the five-row low-level log, or only adding compression while leaving send/response rows intact.
- **Tradeoff**: The feedback log is less granular about provider request boundaries, but much clearer about the actual processing pipeline.

## 2026-03-22: Add 'a' Key to Append Transcriptions
- **Choice**: Space starts new transcription, 'a' appends to existing text.
- **Reason**: Allows speakers to take breaks without including pauses in speech-to-text.
- **Considered**: Always appending, requiring manual clear.
- **Tradeoff**: Users must remember 'a' for append vs Space for new.

## 2026-03-22: Name TUI Focus States Explicitly
- **Choice**: Define the two keyboard contexts as `Command Mode` and `Pane Focus Mode`, and surface the active mode in the status panel.
- **Reason**: The TUI already behaved like a modal interface; making the modes explicit clarifies why global hotkeys like `Space`, `A`, `W`, and `Q` only work after leaving pane focus with `Esc`.
- **Considered**: Leaving the behavior implicit, or renaming the second mode to `Edit Mode`.
- **Tradeoff**: Adds more mode wording to the UI, but reduces confusion and makes focus-sensitive behavior easier to maintain.

## 2026-03-22: Distinguish Overwritten vs New File for 'w' Hotkey
- **Choice**: Check file existence before writing and show distinct messages.
- **Reason**: Users need clear feedback whether a file was created new or overwritten.
- **Considered**: Always showing "saved" without distinction.
- **Tradeoff**: Adds a file existence check before each write operation.

## 2026-03-22: Show Save Confirmation Message After Ctrl+S
- **Choice**: Set status text AFTER calling `action_enter_command_mode()` so the save message is visible.
- **Reason**: The save confirmation was immediately overwritten by the default status message.
- **Considered**: Adding a timed notification system, or keeping focus on editor after save.
- **Tradeoff**: Users now see the save confirmation briefly before the UI returns to default state.

## 2026-03-22: Add 'w' Hotkey to Write Selected Prompt to /tmp/issue.md
- **Choice**: Added 'w' key binding in command mode to export the currently selected transcription to /tmp/issue.md as Markdown.
- **Reason**: Users need a quick way to export a transcription (summary + full text) for issue creation or further processing.
- **Considered**: Adding a copy-to-clipboard variant, or prompting for filename.
- **Tradeoff**: Fixed output path (/tmp/issue.md) means only one prompt at a time; users who need multiple prompts must rename or copy the file manually.

## 2026-03-22: Return To Command Mode After Ctrl+S Save
- **Choice**: After successfully saving a transcript with Ctrl+S, automatically call `action_enter_command_mode()` to return the TUI to Command Mode.
- **Reason**: The user workflow is typically: record → edit → save → copy. Requiring an extra Escape press after save is unintuitive and slows down the common case.
- **Considered**: Keeping focus on the editor after save so users can continue editing.
- **Tradeoff**: Users who want to edit more after saving must press Tab to re-enter the editor instead of just continuing to type. The save-then-copy workflow is more common than save-then-edit-more.

## 2026-03-22: Split TUI Status Into State And Flash Fields
- **Choice**: Replace the overloaded single status area with two one-line fields: a persistent `State` field and a persistent `Flash` feedback field.
- **Reason**: Mode changes, recording state, and action confirmations were overwriting each other and causing inconsistent user feedback, especially after mouse focus changes.
- **Considered**: Keeping one status field with more complex priority rules, or using timed disappearing notifications.
- **Tradeoff**: The UI adds one more explicit field, but status semantics become much simpler and feedback messages remain visible until replaced.

## 2026-03-22: Remove Redundant Ctrl+Shift+C Copy Binding
- **Choice**: Keep `C` as the transcript copy hotkey and remove the duplicate `Ctrl+Shift+C` binding.
- **Reason**: The duplicate binding was unnecessary once explicit copy feedback was restored through the new flash-message field.
- **Considered**: Keeping both bindings for compatibility.
- **Tradeoff**: Users accustomed to `Ctrl+Shift+C` must switch to `C`, but the binding surface is simpler and less confusing.

## 2026-03-22: Append Renders From Selected Saved Transcript
- **Choice**: In append mode, derive the display and append base text from the selected saved transcript entry rather than the transient editor contents.
- **Reason**: Mouse/focus interactions could leave stale editor text visible, causing append to target the correct DB row while temporarily rendering the wrong transcript in the pane.
- **Considered**: Continuing to use editor text as the append base, or trying to synchronize editor text more aggressively.
- **Tradeoff**: Append now depends on a saved selection being present, but the rendered transcript and persisted transcript always use the same source of truth.

## 2026-03-27: Use DELETE Journal Mode for SQLite Cloud Sync Compatibility
- **Choice**: Explicitly set `PRAGMA journal_mode=DELETE` in the SQLite connection method for `prompts.sqlite`.
- **Reason**: Cloud storage services (OneDrive, Dropbox, etc.) do not work well with SQLite WAL mode because the `-wal` and `-shm` files cause sync conflicts and potential corruption.
- **Considered**: Leaving the default (DELETE on most systems) without explicit pragma, or documenting that the database file must not be placed in cloud-synced directories.
- **Tradeoff**: DELETE mode has slightly worse concurrent-write performance than WAL, but this is irrelevant for single-user desktop transcription history.

## 2026-03-27: Add Skill Source Pre-Check To AGENTS.md
- **Choice**: Add a prominent PRE-CHECK section at the top of AGENTS.md instructing the agent to use only workspace `skills/` directory and ignore OpenClaw bundled skills.
- **Reason**: The `available_skills` list in the system prompt appears before AGENTS.md, causing the agent to see "github skill available" before reading the prohibition.
- **Considered**: Relying on the existing "Framework Isolation" section further down the file.
- **Tradeoff**: Adds a redundant-looking section at the top, but prevents the agent from using wrong skills when it reads top-to-bottom.

## 2026-05-31: Errors Must Never Fail Silently — Use Modal ErrorDialog
- **Choice**: Every caught exception must be user-visible. In TUI mode, a modal `ErrorDialog(ModalScreen)` with an OK button; in CLI mode, a `console.print()` warning/error.
- **Reason**: 16 locations silently swallowed exceptions via `pass` or bare `return`, causing confusing downstream failures (e.g., `stt_client = None` → later `AssertionError` with no context).
- **Considered**: Adding a logging module (stdlib or loguru), using `stderr` prints, keeping existing silent catch.
- **Tradeoff**: `core.py` functions no longer silently fall back on ffmpeg failure; the exception propagates to the caller which shows a dialog. Setup errors (missing ffmpeg, invalid API keys) abort the app with a clear message where before they silently degraded.

## 2026-06-11: Move LLM Prompts To Configurable prompts.toml
- **Choice**: Extract all LLM prompt strings into `~/.config/aitranscribe/prompts.toml` (TOML format), auto-created from embedded defaults, with strict validation at startup.
- **Reason**: Hardcoded prompt strings in Python source require code changes to customize. The TOML format supports multiline strings natively, is human-editable, and `tomllib` is stdlib since Python 3.11 (no extra deps).
- **Considered**: YAML (requires PyYAML dep), JSON (poor multiline support), extending dotenv config (no multiline support).
- **Tradeoff**: Adds a second config file alongside the existing dotenv config, but TOML is purpose-built for this use case and the separation keeps API keys and prompt text in their natural formats.

## 2026-06-11: Adopt polished-recognition Prompt Structure
- **Choice**: Use separate system prompt (constraints only) and user message (task instruction + data) with a translation sub-template injected into the user message via `{{translate}}` placeholder.
- **Reason**: The polished-recognition project demonstrated a cleaner structure: system contains rules, user contains the task description and data, and translation is a sub-template resolved before injection. This always produces exactly 2 messages to the LLM.
- **Considered**: Appending the user's request to the system prompt (old pattern), or sending 3 messages (system, task, data).
- **Tradeoff**: Three different message builders are needed (post_process, summary, translate), but each is simple and the assembly logic is clear.

## 2026-03-11: Make Sidebar History Fill Remaining Height And Re-Refresh After Mount
- **Choice**: Let the `Transcriptions` panel consume the remaining sidebar height with `height: 1fr` while `Recording Mode` and `Configuration` stay auto-sized, and trigger a second history refresh after the first layout pass on startup.
- **Reason**: The right column should mirror the left column's behavior, and startup history previews need the same stable width calculation that later refreshes already use.
- **Considered**: Tweaking only container heights, or relying on the initial mount refresh without a post-layout rerender.
- **Tradeoff**: Startup performs one extra history-list rebuild, but the panel height and truncation become visually correct immediately.
