"""Seam conditioning for live fragments (port of polished-recognition's seam work).

Every fragment seam gets three coupled measures, all driven by the previous
fragment's transcript:

* **Pre-roll**: the last second of the previous fragment's audio is prepended to
  the upload, so the service hears the words on both sides of the cut.
* **Prompt carry-over**: a seam-local prompt built from the previous transcript
  tail (<= 96 characters, cut at a word boundary) gives the model the spelling
  and context of the last words.
* **Echo trim**: the transcript head is matched against the previous transcript
  tail (<= 8 tokens, head token must match, at most one mismatch for k >= 2);
  a match is removed so the pre-roll does not produce duplicated words.

The original gates these measures behind its silence-quality threshold; this
project now ports that gate: a seam is conditioned only when its Q is below
`[recording].seam_quality_min` (`main.LiveTranscriptionSession`).
"""

from __future__ import annotations

PRE_ROLL_SECONDS = 1.0
SEAM_PROMPT_MAX_CHARS = 96
ECHO_MAX_TOKENS = 8


def seam_prompt(previous_text: str, max_chars: int = SEAM_PROMPT_MAX_CHARS) -> str | None:
    """The last `max_chars` characters of the previous transcript, word-aligned."""
    text = (previous_text or "").strip()
    if not text:
        return None
    if len(text) <= max_chars:
        return text
    tail = text[-max_chars:]
    space = tail.find(" ")
    if space > 0:
        tail = tail[space + 1:]
    tail = tail.strip()
    return tail or None


def trim_echo(
    text: str, previous_text: str, max_tokens: int = ECHO_MAX_TOKENS
) -> tuple[str, int]:
    """Remove a transcript head that repeats the previous transcript's tail.

    Conservative by design: the first token must match exactly, longer matches
    tolerate one mismatch, and without a match everything is kept. The pre-roll
    makes the service repeat the seam words; this removes exactly that echo.

    Returns ``(text, removed_tokens)`` so the STT log can record how much the
    trim actually ate.
    """
    tokens = (text or "").split()
    previous = (previous_text or "").split()
    if not tokens or not previous:
        return text, 0

    limit = min(max_tokens, len(tokens), len(previous))
    for size in range(limit, 0, -1):
        head = tokens[:size]
        tail = previous[-size:]
        if head[0].lower() != tail[0].lower():
            continue
        mismatches = sum(
            1 for left, right in zip(head, tail) if left.lower() != right.lower()
        )
        if mismatches == 0 or (size >= 2 and mismatches <= 1):
            return " ".join(tokens[size:]).strip(), size
    return text, 0
