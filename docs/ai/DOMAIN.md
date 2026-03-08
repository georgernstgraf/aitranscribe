# Domain Knowledge

Business rules and domain relationships not obvious from code.

## Entities
- prompt queue entry: stored transcription text plus source filename, creation timestamp, and `played_count` used to track unread vs read state.

## Rules
- The TUI transcript panel should show only the final displayed result, so when preprocessing runs the post-processed text replaces the raw transcript in the main transcript view.
- Unread transcription history is defined as queue entries with `played_count = 0`, and the TUI "mark all as read" action converts all unread entries to read in one operation.
- Transcript output must remain mouse-selectable so users can copy text from the terminal and paste it into other applications.
- The transcript panel doubles as a full-message preview for unread history: when the user highlights an unread entry with the arrow keys, that entry's complete text should replace the current idle transcript view.
- The TUI must provide an explicit transcript-copy action because visual mouse selection in the fullscreen interface is not sufficient for cross-application paste.
