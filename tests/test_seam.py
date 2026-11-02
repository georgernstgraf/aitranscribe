"""Contracts for seam conditioning: prompt carry-over and echo trim."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from seam import ECHO_MAX_TOKENS, SEAM_PROMPT_MAX_CHARS, seam_prompt, trim_echo


# --------------------------------------------------------------------------- #
# Prompt carry-over
# --------------------------------------------------------------------------- #
def test_prompt_keeps_a_short_transcript_verbatim():
    assert seam_prompt("Der Schnitt liegt in einer Pause.") == "Der Schnitt liegt in einer Pause."


def test_prompt_is_empty_for_an_empty_transcript():
    assert seam_prompt("") is None
    assert seam_prompt("   ") is None


def test_prompt_takes_the_tail_and_cuts_at_a_word_boundary():
    text = "wort " * 40 + "die letzten Worte der Diktate"

    prompt = seam_prompt(text)

    assert prompt is not None
    assert len(prompt) <= SEAM_PROMPT_MAX_CHARS
    assert prompt.endswith("die letzten Worte der Diktate")
    assert not prompt.startswith(" ")  # no partial word at the start


def test_prompt_never_exceeds_the_character_budget():
    prompt = seam_prompt("a" * 500)

    assert prompt is not None
    assert len(prompt) <= SEAM_PROMPT_MAX_CHARS


# --------------------------------------------------------------------------- #
# Echo trim
# --------------------------------------------------------------------------- #
def test_echo_trim_removes_an_exact_repeated_head():
    previous = "Wir sprechen über die Naht und den Schnitt."
    text = "und den Schnitt. Danach geht es weiter."

    assert trim_echo(text, previous) == ("Danach geht es weiter.", 3)


def test_echo_trim_tolerates_one_mismatch_for_multiple_tokens():
    previous = "Wir sprechen über die Naht und den Schnitt"
    text = "und der Schnitt Danach geht es weiter."

    assert trim_echo(text, previous) == ("Danach geht es weiter.", 3)


def test_echo_trim_requires_the_head_token_to_match():
    previous = "Wir sprechen über die Naht."
    text = "Schnitt Danach geht es weiter."

    assert trim_echo(text, previous) == ("Schnitt Danach geht es weiter.", 0)


def test_echo_trim_keeps_everything_without_a_match():
    previous = "Wir sprechen über die Naht."
    text = "Ein völlig neuer Satz beginnt hier."

    assert trim_echo(text, previous) == (text, 0)


def test_echo_trim_keeps_everything_when_nothing_was_heard_before():
    assert trim_echo("Erster Satz.", "") == ("Erster Satz.", 0)
    assert trim_echo("", "Vorheriger Satz.") == ("", 0)


def test_echo_trim_never_removes_more_than_the_token_window():
    previous = " ".join(f"w{index}" for index in range(30))
    text = " ".join(f"w{index}" for index in range(22, 30)) + " neuer Inhalt"

    trimmed, removed = trim_echo(text, previous)

    # Exactly ECHO_MAX_TOKENS tokens are matched; the rest of the repeat stays.
    assert trimmed == "neuer Inhalt"
    assert removed == ECHO_MAX_TOKENS


def test_echo_trim_is_case_insensitive():
    previous = "Die Naht und der Schnitt"
    text = "die naht und der schnitt Danach"

    assert trim_echo(text, previous) == ("Danach", 5)


def test_echo_trim_returns_the_whole_text_when_the_echo_is_the_whole_text():
    previous = "und den Schnitt"
    text = "und den Schnitt"

    assert trim_echo(text, previous) == ("", 3)
