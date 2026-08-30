# Handoff

Pending tasks are tracked as GitHub sub-issues of #63 (code audit remediation):

1. [ ] See #68 — Replace production asserts with typed errors + guard LLM response access (1st priority)
2. [ ] See #69 — Add core.py test coverage (2nd)
3. [ ] See #70 — Move module-level side effects out of main.py import (3rd)
4. [ ] See #71 — Deduplicate audio pipeline logic (4th)
5. [ ] See #72 — Config and state robustness (5th)
6. [ ] See #67 — Set Linux terminal title to current app name (untriaged)

Rules: never close #63 while sub-issues are open. Uncommitted docs/ai/ knowledge file edits may exist — commit them with the next code change or ask the user.

Last updated: 2026-08-30.
