# Domain Knowledge

Business rules and domain relationships not obvious from code.

## Entities
- prompt queue entry: stored transcription text plus source filename and creation timestamp; entries are plain saved history without unread/read tracking.

## Rules
- The TUI transcript panel should show only the final displayed result, so when preprocessing runs the post-processed text replaces the raw transcript in the main transcript view.
- Saved transcription history includes all stored entries, and queue storage is always on for TUI-triggered transcriptions.
- Transcript output must remain mouse-selectable so users can copy text from the terminal and paste it into other applications.
- The transcript panel doubles as a full-message preview for stored history: when the user highlights an entry with the arrow keys, that entry's complete text should replace the current idle transcript view.
- The TUI must provide an explicit transcript-copy action because visual mouse selection in the fullscreen interface is not sufficient for cross-application paste.
- The TUI `Recording Mode` panel must support both live microphone capture and filesystem audio-file transcription, with `english` as the default preprocessing mode.
