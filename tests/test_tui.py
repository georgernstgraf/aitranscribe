import os
from io import StringIO
from unittest.mock import Mock
from unittest.mock import patch

from tui import AitranscribeTUI, build_osc52_sequence, copy_text_to_clipboard, copy_text_with_osc52, get_clipboard_command


def test_get_clipboard_command_prefers_wl_copy_on_wayland():
    env = {"WAYLAND_DISPLAY": "wayland-0", "DISPLAY": ":1"}

    with patch("tui.shutil.which") as mock_which:
        mock_which.side_effect = lambda name: {"wl-copy": "/usr/bin/wl-copy", "xclip": "/usr/bin/xclip"}.get(name)
        assert get_clipboard_command(env) == ["wl-copy"]


def test_get_clipboard_command_uses_xclip_on_x11():
    env = {"DISPLAY": ":1"}

    with patch("tui.shutil.which") as mock_which:
        mock_which.side_effect = lambda name: {"xclip": "/usr/bin/xclip"}.get(name)
        assert get_clipboard_command(env) == ["xclip", "-selection", "clipboard"]


def test_get_clipboard_command_falls_back_to_pbcopy_without_display():
    env = {}

    with patch("tui.shutil.which") as mock_which:
        mock_which.side_effect = lambda name: {"pbcopy": "/usr/bin/pbcopy"}.get(name)
        assert get_clipboard_command(env) == ["pbcopy"]


def test_copy_text_to_clipboard_runs_detected_command():
    with patch.dict(os.environ, {"WAYLAND_DISPLAY": "wayland-0"}, clear=True):
        with patch("tui.shutil.which", return_value="/usr/bin/wl-copy"):
            with patch("tui.subprocess.run") as mock_run:
                assert copy_text_to_clipboard("hello") is True
                mock_run.assert_called_once_with(["wl-copy"], input="hello", text=True, check=True)


def test_build_osc52_sequence_wraps_for_tmux():
    sequence = build_osc52_sequence("hello", {"TMUX": "1"})
    assert sequence.startswith("\033Ptmux;\033\033]52;c;")
    assert sequence.endswith("\a\033\\")


def test_copy_text_with_osc52_writes_escape_sequence():
    stream = StringIO()
    assert copy_text_with_osc52("hello", stream=stream, environ={"TERM": "xterm-256color"}) is True
    assert "\033]52;c;" in stream.getvalue()


def test_copy_text_to_clipboard_falls_back_to_osc52():
    stream = StringIO()
    with patch("tui.shutil.which", return_value=None):
        with patch("tui.sys.stdout", stream):
            assert copy_text_to_clipboard("hello") is True
            assert "\033]52;c;" in stream.getvalue()


def test_history_selection_controls_displayed_transcript():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
    )
    app.latest_transcript = "Newest transcript"
    app.history_prompts = [{"id": 7, "prompt": "Stored unread transcript"}]

    app.select_history_prompt(0)

    assert app.selected_history_id == 7
    assert app.get_displayed_transcript() == "Stored unread transcript"


def test_displayed_transcript_returns_latest_while_processing():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
    )
    app.latest_transcript = "Waiting for transcription..."
    app.selected_history_text = "Stored unread transcript"
    app.is_processing = True

    assert app.get_displayed_transcript() == "Waiting for transcription..."
