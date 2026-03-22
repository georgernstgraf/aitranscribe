import os
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import Mock
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from tui import AitranscribeTUI, build_osc52_sequence, copy_text_to_clipboard, copy_text_with_osc52, get_clipboard_command
from textual.containers import Vertical
from textual.widgets import Input, OptionList, Static, TextArea


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
    """Test OSC52 fallback only works when a terminal is available."""
    # Skip if no terminal environment (OSC52 requires TERM, TMUX, or TERM_PROGRAM)
    has_terminal = any(key in os.environ for key in ("TERM", "TMUX", "TERM_PROGRAM"))
    if not has_terminal:
        pytest.skip("OSC52 fallback requires a terminal environment (TERM, TMUX, or TERM_PROGRAM)")

    stream = StringIO()
    with patch("tui.shutil.which", return_value=None):
        with patch("tui.sys.stdout", stream):
            assert copy_text_to_clipboard("hello") is True
            assert "\033]52;c;" in stream.getvalue()


def test_history_selection_controls_displayed_transcript():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.latest_transcript = "Newest transcript"
    app.history_prompts = [{"id": 7, "prompt": "Stored unread transcript", "summary": None}]

    app.select_history_prompt(0)

    assert app.selected_history_id == 7
    assert app.get_displayed_transcript() == "Stored unread transcript"


def test_displayed_transcript_returns_latest_while_processing():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.latest_transcript = "Waiting for transcription..."
    app.selected_history_text = "Stored unread transcript"
    app.is_processing = True

    assert app.get_displayed_transcript() == "Waiting for transcription..."


def test_tui_uses_english_as_default_preprocess_mode():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    assert app.pre_process_mode == "english"


def test_tui_keeps_verbose_from_config_without_widget():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone", "verbose": True},
    )

    assert app.verbose is True


def test_is_command_mode_without_focused_widget():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    with patch.object(type(app), "focused", new_callable=lambda: property(lambda _self: None)):
        assert app.is_command_mode() is True
        assert app.is_pane_focus_mode() is False


def test_is_pane_focus_mode_with_history_list_focus():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    focused = Mock(id="history_list")

    with patch.object(type(app), "focused", new_callable=lambda: property(lambda _self: focused)):
        assert app.is_pane_focus_mode() is True
        assert app.is_command_mode() is False


def test_feedback_steps_include_compress_stage_first():
    app = AitranscribeTUI(
        prompt_manager=Mock(),
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    assert app.FEEDBACK_STEPS == [
        ("compress", "Compressing Message"),
        ("transcribe", "Transcribing Raw Message"),
        ("post_process", "Post-Processing Message"),
        ("summary", "Creating Summary"),
    ]
    assert app.feedback_state["compress"] == "pending"


@pytest.mark.anyio
async def test_refresh_feedback_renders_compress_stage():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        app.update_feedback_state("compress", "done")
        feedback_text = app.query_one("#feedback_panel", Static).render()

    assert "Compressing Message" in str(feedback_text)


@pytest.mark.anyio
async def test_refresh_status_shows_command_mode_hint():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        app.action_enter_command_mode()
        state_text = str(app.query_one("#state_status", Static).render())
        flash_text = str(app.query_one("#flash_status", Static).render())

    assert state_text == "Command Mode | Ready"
    assert flash_text == ""


@pytest.mark.anyio
async def test_refresh_status_shows_pane_focus_mode_hint():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        history_list = app.query_one("#history_list", OptionList)
        app.set_focus(history_list)
        app.refresh_status()
        state_text = str(app.query_one("#state_status", Static).render())

    assert state_text == "Pane Focus Mode | Ready"


@pytest.mark.anyio
async def test_click_focus_updates_status_to_pane_focus_mode():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test() as pilot:
        editor = app.query_one("#transcript_editor", TextArea)
        app.action_enter_command_mode()
        await pilot.pause()
        app.set_focus(editor)
        await pilot.pause()
        state_text = str(app.query_one("#state_status", Static).render())

    assert state_text == "Pane Focus Mode | Ready"


@pytest.mark.anyio
async def test_recording_status_overrides_command_mode_idle_message():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.is_recording = True
    app.append_mode = False
    app.status_text = "Press Space to Start Recording"

    async with app.run_test():
        app.refresh_status()
        state_text = str(app.query_one("#state_status", Static).render())

    assert state_text == "Pane Focus Mode | Recording: Press Space to Finish"


@pytest.mark.anyio
async def test_append_processing_status_stays_visible_in_pane_focus_mode():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.is_processing = True
    app.append_mode = True
    app.status_text = "Saved transcription #7."

    async with app.run_test() as pilot:
        editor = app.query_one("#transcript_editor", TextArea)
        app.set_focus(editor)
        await pilot.pause()
        state_text = str(app.query_one("#state_status", Static).render())

    assert state_text == "Pane Focus Mode | Appending"


@pytest.mark.anyio
async def test_save_feedback_remains_visible_after_returning_to_command_mode():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]
    prompt_manager.update_prompt.return_value = True

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test() as pilot:
        editor = app.query_one("#transcript_editor", TextArea)
        editor.text = "Edited transcript"
        app.set_focus(editor)
        await pilot.pause()
        app.action_save_transcript()
        await pilot.pause()
        state_text = str(app.query_one("#state_status", Static).render())
        flash_text = str(app.query_one("#flash_status", Static).render())

    assert state_text == "Command Mode | Ready"
    assert flash_text == "Saved transcription #7."


@pytest.mark.anyio
async def test_copy_feedback_uses_flash_status_field():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    with patch("tui.copy_text_to_clipboard", return_value=True):
        async with app.run_test():
            editor = app.query_one("#transcript_editor", TextArea)
            editor.text = "Copied text"
            app.action_copy_transcript()
            flash_text = str(app.query_one("#flash_status", Static).render())

    assert flash_text == "Copied transcript to clipboard."


@pytest.mark.anyio
async def test_write_issue_feedback_uses_flash_status_field():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": "Issue title"},
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.selected_history_id = 7
    app.selected_history_text = "Stored transcript"
    app.history_prompts = prompt_manager.recent_prompts.return_value

    with patch("tui.os.path.exists", return_value=False):
        with patch("builtins.open", create=True) as mock_open:
            async with app.run_test():
                app.action_write_issue()
                flash_text = str(app.query_one("#flash_status", Static).render())

    assert flash_text == "/tmp/issue.md was written."
    assert mock_open.called


@pytest.mark.anyio
async def test_refresh_feedback_preserves_summary_prefix_on_startup():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test() as pilot:
        feedback_panel = app.query_one("#feedback_panel", Static)
        await pilot.pause()
        rendered = feedback_panel.render()

    assert str(rendered).splitlines()[-1].startswith("[ ] Creating Summary")


def test_update_transcript_from_worker_replaces_waiting_text():
    prompt_manager = Mock()

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    with patch.object(app, "refresh_transcript") as mock_refresh:
        app.latest_transcript = "Waiting for transcription..."
        app.update_transcript_from_worker("Raw transcript")

    assert app.raw_transcript == "Raw transcript"
    assert app.latest_transcript == "Raw transcript"
    mock_refresh.assert_called_once()


def test_update_transcript_from_worker_appends_in_append_mode():
    prompt_manager = Mock()

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    app.append_mode = True
    app.append_base_text = "First transcript"  # The base text to append to
    app.latest_transcript = "First transcript"

    with patch.object(app, "refresh_transcript") as mock_refresh:
        app.update_transcript_from_worker("Second transcript")

    assert app.raw_transcript == "Second transcript"
    assert app.latest_transcript == "First transcript\n\nSecond transcript"
    mock_refresh.assert_called_once()


def test_update_transcript_from_worker_append_without_base_uses_new_text():
    prompt_manager = Mock()

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    app.append_mode = True
    app.append_base_text = ""

    with patch.object(app, "refresh_transcript") as mock_refresh:
        app.update_transcript_from_worker("New transcript")

    assert app.latest_transcript == "New transcript"
    mock_refresh.assert_called_once()


def test_processing_finished_updates_selected_prompt_in_append_mode():
    prompt_manager = Mock()
    prompt_manager.update_prompt.return_value = True

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    app.append_mode = True
    app.append_target_id = 7
    app.append_base_text = "First transcript"

    with patch.object(app, "refresh_transcript") as mock_refresh:
        with patch.object(app, "refresh_status") as mock_status:
            with patch.object(app, "refresh_history") as mock_history:
                with patch.object(app, "run_worker") as mock_worker:
                    app.processing_finished({"text": "Second transcript", "file_path": "/tmp/a.mp3", "prompt_id": "99"})

    prompt_manager.update_prompt.assert_called_once_with(7, "First transcript\n\nSecond transcript")
    assert app.latest_transcript == "First transcript\n\nSecond transcript"
    assert app.selected_history_id == 7
    assert app.selected_history_text == "First transcript\n\nSecond transcript"
    assert app.append_mode is False
    assert app.append_target_id is None
    assert app.append_base_text == ""
    mock_refresh.assert_called_once()
    mock_status.assert_called_once()
    mock_history.assert_called_once()
    mock_worker.assert_called_once()


def test_action_append_recording_requires_selected_saved_transcript():
    prompt_manager = Mock()

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    with patch.object(app, "is_pane_focus_mode", return_value=False):
        with patch.object(app, "start_recording") as mock_start:
            with patch.object(app, "refresh_status") as mock_status:
                app.action_append_recording()

    assert app.append_mode is False
    assert app.append_target_id is None
    assert app.append_base_text == ""
    assert app.status_text == "Select a saved transcription before appending."
    mock_start.assert_not_called()
    mock_status.assert_called_once()


def test_action_append_recording_uses_selected_saved_transcript_as_base():
    prompt_manager = Mock()

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    app.selected_history_id = 42
    app.selected_history_text = "This is a historical transcript from the history list."

    with patch.object(app, "is_pane_focus_mode", return_value=False):
        with patch.object(app, "get_editor_text", return_value="This is a historical transcript from the history list."):
            with patch.object(app, "start_recording") as mock_start:
                app.action_append_recording()

    assert app.append_mode is True
    assert app.append_target_id == 42
    assert app.append_base_text == "This is a historical transcript from the history list."
    assert app.latest_transcript == "This is a historical transcript from the history list."
    mock_start.assert_called_once()


def test_start_recording_preserves_append_base_text_in_editor_state():
    prompt_manager = Mock()

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.append_mode = True
    app.append_base_text = "Previously stored transcript"

    with patch.object(app.recorder, "start"):
        with patch.object(app, "reset_feedback"):
            with patch.object(app, "refresh_status"):
                with patch.object(app, "refresh_transcript"):
                    app.start_recording()

    assert app.latest_transcript == "Previously stored transcript"


@pytest.mark.anyio
async def test_refresh_history_requests_full_history_list():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 2
    prompt_manager.recent_prompts.return_value = [
        {"id": 2, "prompt": "Newest", "filename": "b.mp3", "timestamp": "2026-03-09T12:00:00", "summary": None},
        {"id": 1, "prompt": "Older", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        prompt_manager.recent_prompts.assert_called_with()

    assert prompt_manager.recent_prompts.call_count >= 1


@pytest.mark.anyio
async def test_file_path_input_accepts_keyboard_entry():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "file"},
    )

    async with app.run_test() as pilot:
        file_input = app.query_one("#file_path", Input)
        app.set_focus(file_input)
        await pilot.press("/", "t", "m", "p", "/", "a", ".", "m", "p", "3")
        assert file_input.value == "/tmp/a.mp3"


@pytest.mark.anyio
async def test_save_transcript_updates_selected_history_entry():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]
    prompt_manager.update_prompt.return_value = True

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        editor = app.query_one("#transcript_editor", TextArea)
        editor.text = "Edited transcript"
        app.action_save_transcript()

    prompt_manager.update_prompt.assert_called_with(7, "Edited transcript")


@pytest.mark.anyio
async def test_delete_selected_transcription_uses_delete_key_on_history_list():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]
    prompt_manager.remove_prompt_by_id.return_value = True

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        history_list = app.query_one("#history_list", OptionList)
        app.set_focus(history_list)
        app.action_delete_selected_transcription()

    prompt_manager.remove_prompt_by_id.assert_called_with(7)


@pytest.mark.anyio
async def test_copy_action_copies_full_editor_text_while_editing():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 0
    prompt_manager.recent_prompts.return_value = []

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )
    app.latest_transcript = "Edited transcript\nSecond line"

    with patch("tui.copy_text_to_clipboard", return_value=True) as mock_copy:
        async with app.run_test() as pilot:
            editor = app.query_one("#transcript_editor", TextArea)
            app.set_focus(editor)
            editor.text = "Edited transcript\nSecond line"
            await pilot.pause()
            app.action_copy_transcript()

    mock_copy.assert_called_with("Edited transcript\nSecond line")


@pytest.mark.anyio
async def test_refresh_history_prefers_summary_text_in_list_entries():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {
            "id": 7,
            "prompt": "Full transcript body that should not be used in the list when summary exists.",
            "filename": "a.mp3",
            "timestamp": "2026-03-09T11:00:00",
            "summary": "Short generated summary for list preview.",
        },
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        history_list = app.query_one("#history_list", OptionList)
        option_prompt = history_list.get_option_at_index(0).prompt

    assert "Short generated summary" in str(option_prompt)
    assert "Full transcript body" not in str(option_prompt)


@pytest.mark.anyio
async def test_refresh_history_uses_full_available_width_before_ellipsis():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {
            "id": 7,
            "prompt": "ignored full transcript body",
            "filename": "a.mp3",
            "timestamp": "2026-03-09T11:00:00",
            "summary": "12345678901234567890",
        },
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    async with app.run_test():
        history_list = app.query_one("#history_list", OptionList)
        history_panel = app.query_one("#history_panel", Vertical)
        history_list.styles.width = 30
        history_panel.styles.width = 30
        app.refresh_history()
        option_prompt = str(history_list.get_option_at_index(0).prompt)

    assert option_prompt == "#7: 12345678901234567890"


@pytest.mark.anyio
async def test_on_mount_schedules_second_history_refresh_after_layout():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {
            "id": 7,
            "prompt": "ignored transcript body",
            "filename": "a.mp3",
            "timestamp": "2026-03-09T11:00:00",
            "summary": "Startup width should match post-transcription width",
        },
    ]

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
    )

    with patch.object(app, "refresh_history", wraps=app.refresh_history) as mock_refresh:
        async with app.run_test():
            pass

    assert mock_refresh.call_count >= 2


@pytest.mark.anyio
async def test_processing_finished_starts_background_summary_generation_for_saved_prompt():
    prompt_manager = Mock()
    prompt_manager.count_prompts.return_value = 1
    prompt_manager.recent_prompts.return_value = [
        {"id": 7, "prompt": "Stored transcript", "filename": "a.mp3", "timestamp": "2026-03-09T11:00:00", "summary": None},
    ]
    prompt_manager.update_prompt_summary.return_value = True

    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=Mock(),
        process_file=Mock(),
        stt_provider_name="Groq",
        llm_provider_name="openrouter",
        default_stt_model="whisper",
        default_llm_model="gpt",
        initial_settings={"pre_process_mode": "english", "input_source": "microphone"},
        generate_summary=Mock(return_value="Generated summary"),
    )

    async with app.run_test():
        app.processing_finished({"text": "Fresh transcript", "file_path": "/tmp/a.mp3", "prompt_id": "7"})
        await app.workers.wait_for_complete()

    prompt_manager.update_prompt_summary.assert_called_with(7, "Generated summary")
