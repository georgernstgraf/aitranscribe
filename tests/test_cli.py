import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
import tempfile
import os
import sqlite3

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

# We import the main app. If dependencies like typer are missing,
# this import will fail immediately, thus failing the test suite.
try:
    from main import (
        app,
        post_process_option,
        stt_model_option,
        llm_model_option,
        verbose_option,
        english_option,
        help_option,
        file_option,
        file_path_argument,
        list_prompts_option,
        query_prompt_option,
        remove_prompt_option,
        get_pre_process_prompt,
        validate_api_keys,
        wrap_text,
        build_post_process_messages,
        build_summary_messages,
        build_translate_messages,
        get_recording_file_paths,
        get_tui_settings,
        launch_tui,
        backfill_missing_summaries,
        console,
        CONFIG_FILE,
        stt_client,
        llm_client,
        PROMPTS,
        PromptManager,
    )
except ImportError as e:
    pytest.fail(f"Failed to import the CLI app due to missing dependencies: {e}")

runner = CliRunner()

def test_config_dir_path_selection():
    """Test that CONFIG_DIR selection logic works correctly based on OS."""
    from pathlib import PurePath, PureWindowsPath, PurePosixPath
    
    # Test Windows selection logic
    appdata = 'C:\\Users\\FakeUser\\AppData\\Roaming'
    config_dir = PureWindowsPath(appdata) / "aitranscribe"
    assert str(config_dir) == 'C:\\Users\\FakeUser\\AppData\\Roaming\\aitranscribe'

    # Test Linux selection logic
    home = '/home/fakeuser'
    config_dir = PurePosixPath(home) / ".config" / "aitranscribe"
    assert str(config_dir) == '/home/fakeuser/.config/aitranscribe'

def test_cli_file_missing_arg():
    """Test that --file option defaults to /tmp/aitranscribe_record.mp3."""
    result = runner.invoke(app, ["--file", "/tmp/aitranscribe_record.mp3"])
    # Should fail because of default file does not exist in testing
    assert result.exit_code != 0
    assert "File not found" in result.stdout
    assert "/tmp/aitranscribe_record.mp3" in result.stdout


def test_cli_defaults_to_tui_launch():
    """Test that running without arguments launches the TUI."""
    with patch("main.launch_tui") as mock_launch_tui:
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        mock_launch_tui.assert_called_once()


# ==================== Option Factory Tests ====================

def test_post_process_option():
    """Test that post_process_option returns correct typer.Option."""
    option = post_process_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_stt_model_option():
    """Test that stt_model_option returns correct typer.Option."""
    option = stt_model_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_llm_model_option():
    """Test that llm_model_option returns correct typer.Option."""
    option = llm_model_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_verbose_option():
    """Test that verbose_option returns correct typer.Option."""
    option = verbose_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_english_option():
    """Test that english_option returns correct typer.Option."""
    option = english_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_help_option():
    """Test that help_option returns correct typer.Option."""
    option = help_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_file_path_argument():
    """Test that file_path_argument returns correct typer.Argument."""
    argument = file_path_argument()
    assert isinstance(argument, typer.models.ArgumentInfo)

def test_file_option():
    """Test that file_option returns correct typer.Option."""
    option = file_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_list_prompts_option():
    """Test that list_prompts_option returns correct typer.Option."""
    option = list_prompts_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_query_prompt_option():
    """Test that query_prompt_option returns correct typer.Option."""
    option = query_prompt_option()
    assert isinstance(option, typer.models.OptionInfo)

def test_remove_prompt_option():
    """Test that remove_prompt_option returns correct typer.Option."""
    option = remove_prompt_option()
    assert isinstance(option, typer.models.OptionInfo)

# ==================== Logic Helper Tests ====================

def test_build_post_process_messages_cleanup_only():
    """Test post-process messages without translation target."""
    messages = build_post_process_messages("Hello world", target_language=None)
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "Hello world" in messages[1]["content"]
    assert "correct grammatical errors" in messages[1]["content"]
    assert "{{translate}}" not in messages[1]["content"]
    assert "{{target_language}}" not in messages[1]["content"]


def test_build_post_process_messages_with_translate():
    """Test post-process messages with translation target."""
    messages = build_post_process_messages("Hallo Welt", target_language="English")
    assert len(messages) == 2
    assert "Hallo Welt" in messages[1]["content"]
    assert "correct grammatical errors" in messages[1]["content"]
    assert "English" in messages[1]["content"]
    assert "{{translate}}" not in messages[1]["content"]


def test_build_summary_messages():
    """Test summary messages construction."""
    messages = build_summary_messages("A long transcript")
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert "A long transcript" in messages[1]["content"]
    assert "summary" in messages[1]["content"].lower()


def test_build_translate_messages():
    """Test standalone translation messages."""
    messages = build_translate_messages("Guten Tag", target_language="English")
    assert len(messages) == 2
    assert "Guten Tag" in messages[1]["content"]
    assert "Translate" in messages[1]["content"]
    assert "English" in messages[1]["content"]
    assert "{{target_language}}" not in messages[1]["content"]


def test_get_pre_process_prompt_modes():
    """Test TUI preprocessing mode mapping."""
    assert get_pre_process_prompt("raw") is None
    cleanup_prompt = get_pre_process_prompt("cleanup")
    english_prompt = get_pre_process_prompt("english")
    assert cleanup_prompt is None
    assert english_prompt == "English"

def test_get_recording_file_paths_uses_three_digits():
    """Test temp recording filenames use 3-digit versions."""
    temp_dir = tempfile.mkdtemp()

    try:
        Path(os.path.join(temp_dir, "aitranscribe_record_v001.mp3")).touch()
        Path(os.path.join(temp_dir, "aitranscribe_record_v009.mp3")).touch()

        with patch("tempfile.gettempdir", return_value=temp_dir):
            raw_wav, final_audio = get_recording_file_paths(".mp3")

        assert raw_wav == os.path.join(temp_dir, ".aitranscribe_raw.wav")
        assert final_audio == os.path.join(temp_dir, "aitranscribe_record_v010.mp3")
    finally:
        for file_name in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file_name))
        os.rmdir(temp_dir)


def test_get_tui_settings_defaults_to_english_and_microphone(tmp_path):
    """Test TUI settings load new defaults from config."""
    config_file = tmp_path / "config"
    config_file.write_text('PRE_PROCESS_MODE="english"\nTRANSCRIBE_SOURCE="microphone"\nVERBOSE_ERRORS="false"\n')

    with patch("main.CONFIG_FILE", config_file), patch("main.GROQ_STT_MODEL", "whisper"), patch("main.LLM_MODEL", "gpt"):
        settings = get_tui_settings()

    assert settings["pre_process_mode"] == "english"
    assert settings["input_source"] == "microphone"
    assert settings["file_path"] == ""

def test_validate_api_keys_with_stt_client_none():
    """Test that validate_api_keys fails when stt_client is None."""
    with patch('main.stt_client', None):
        with patch('main.console') as mock_console:
            with pytest.raises(typer.Exit) as exc_info:
                validate_api_keys(None)
            assert exc_info.value.exit_code == 1
            mock_console.print.assert_called_once()

def test_validate_api_keys_with_post_process_and_no_llm_client():
    """Test that validate_api_keys fails when post_process requested but llm_client is None."""
    with patch('main.stt_client', MagicMock()):
        with patch('main.llm_client', None):
            with patch('main.console') as mock_console:
                with pytest.raises(typer.Exit) as exc_info:
                    validate_api_keys("test prompt")
                assert exc_info.value.exit_code == 1
                mock_console.print.assert_called_once()

def test_validate_api_keys_success():
    """Test that validate_api_keys passes with valid clients."""
    with patch('main.stt_client', MagicMock()):
        with patch('main.llm_client', MagicMock()):
            validate_api_keys(None)
            validate_api_keys("test prompt")

def test_wrap_text_short():
    """Test that wrap_text doesn't wrap short text."""
    result = wrap_text("Short text", 80)
    assert result == "Short text"

def test_wrap_text_long():
    """Test that wrap_text wraps long text at 80 characters."""
    long_text = "This is a very long text that should be wrapped at exactly eighty characters per line to ensure proper formatting"
    result = wrap_text(long_text, 80)
    lines = result.split('\n')
    assert all(len(line) <= 80 for line in lines)
    assert len(lines) > 1

def test_wrap_text_whitespace():
    """Test that wrap_text breaks at whitespace, not mid-word."""
    text = "This is a test of text wrapping functionality"
    result = wrap_text(text, 20)
    lines = result.split('\n')
    assert len(lines) == 3
    assert lines[0] == "This is a test of"
    assert lines[1] == "text wrapping"
    assert lines[2] == "functionality"

def test_promptmanager_query_prompt_empty():
    """Test PromptManager.query_prompt with empty queue."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        result = manager.query_prompt()
        assert result is None
    finally:
        temp_file.unlink()

def test_promptmanager_query_prompt_success():
    """Test PromptManager.query_prompt retrieves oldest unplayed prompt."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        manager.add_prompt("First prompt", "file1.mp3")
        manager.add_prompt("Second prompt", "file2.mp3")
        
        result = manager.query_prompt()
        assert result == "First prompt"
        assert len(manager.prompts) == 1
        assert manager.prompts[0]['prompt'] == "Second prompt"
    finally:
        temp_file.unlink()

def test_promptmanager_query_prompt_deletes_oldest_prompt():
    """Test PromptManager.query_prompt deletes the returned prompt."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        manager = PromptManager(temp_file)
        manager.add_prompt("Play me", "file1.mp3")

        result = manager.query_prompt()
        assert result == "Play me"
        assert len(manager.prompts) == 0

        with sqlite3.connect(temp_file) as conn:
            rows = conn.execute("SELECT prompt FROM prompts ORDER BY id ASC").fetchall()
            assert rows == []
    finally:
        temp_file.unlink()

def test_promptmanager_list_prompts_empty(capsys):
    """Test PromptManager.list_prompts with empty queue."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        manager.list_prompts()
        captured = capsys.readouterr()
        assert "No prompts stored yet" in captured.out
    finally:
        temp_file.unlink()

def test_promptmanager_list_prompts_populated(capsys):
    """Test PromptManager.list_prompts with populated queue."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        manager.add_prompt("Test prompt", "test.mp3")
        manager.list_prompts()
        captured = capsys.readouterr()
        assert "Stored Prompts:" in captured.out
        assert "Test prompt" in captured.out
        assert "test.mp3" in captured.out
    finally:
        temp_file.unlink()


def test_promptmanager_recent_prompts_returns_all_in_created_at_desc_order():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        manager = PromptManager(temp_file)
        manager.add_prompt("First prompt", "file1.mp3")
        manager.add_prompt("Second prompt", "file2.mp3")
        manager.add_prompt("Third prompt", "file3.mp3")

        with sqlite3.connect(temp_file) as conn:
            conn.execute("UPDATE prompts SET created_at = ? WHERE prompt = ?", ("2026-03-09T10:00:00", "First prompt"))
            conn.execute("UPDATE prompts SET created_at = ? WHERE prompt = ?", ("2026-03-09T11:00:00", "Second prompt"))
            conn.execute("UPDATE prompts SET created_at = ? WHERE prompt = ?", ("2026-03-09T12:00:00", "Third prompt"))

        prompts = manager.recent_prompts()

        assert [prompt["prompt"] for prompt in prompts] == ["Third prompt", "Second prompt", "First prompt"]
    finally:
        temp_file.unlink()


def test_promptmanager_update_prompt_by_id():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        manager = PromptManager(temp_file)
        prompt_id = manager.add_prompt("Original", "file1.mp3")

        assert prompt_id is not None
        assert manager.update_prompt(prompt_id, "Edited") is True
        assert manager.recent_prompts()[0]["prompt"] == "Edited"
    finally:
        temp_file.unlink()


def test_promptmanager_migrates_existing_database_to_add_summary_column():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        with sqlite3.connect(temp_file) as conn:
            conn.execute(
                """
                CREATE TABLE prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )

        manager = PromptManager(temp_file)

        with sqlite3.connect(temp_file) as conn:
            columns = conn.execute("PRAGMA table_info(prompts)").fetchall()

        assert any(column[1] == "summary" for column in columns)
        assert manager.prompts_missing_summary() == []
    finally:
        temp_file.unlink()


def test_promptmanager_can_update_summary_and_return_it_in_recent_prompts():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        manager = PromptManager(temp_file)
        prompt_id = manager.add_prompt("Original transcript", "file1.mp3")

        assert prompt_id is not None
        assert manager.update_prompt_summary(prompt_id, "This is the generated summary text for preview.") is True
        assert manager.recent_prompts()[0]["summary"] == "This is the generated summary text for preview."
    finally:
        temp_file.unlink()


def test_backfill_missing_summaries_updates_only_missing_rows():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        manager = PromptManager(temp_file)
        missing_id = manager.add_prompt("Long transcript that still needs a summary.", "file1.mp3")
        existing_id = manager.add_prompt("Transcript with summary.", "file2.mp3", summary="Existing summary")

        assert missing_id is not None
        assert existing_id is not None

        with patch("main.llm_client", object()):
            with patch("main.process_with_llm", return_value="Fresh generated summary") as mock_process:
                updated = backfill_missing_summaries(manager, "gpt-test")

        prompts = manager.recent_prompts()
        by_id = {prompt["id"]: prompt for prompt in prompts}

        assert updated == 1
        assert by_id[missing_id]["summary"] == "Fresh generated summary"
        assert by_id[existing_id]["summary"] == "Existing summary"
        mock_process.assert_called_once()
    finally:
        temp_file.unlink()


def test_promptmanager_remove_prompt_by_id():
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sqlite', delete=False) as f:
        temp_file = Path(f.name)

    try:
        manager = PromptManager(temp_file)
        prompt_id = manager.add_prompt("To delete", "file1.mp3")

        assert prompt_id is not None
        assert manager.remove_prompt_by_id(prompt_id) is True
        assert manager.count_prompts() == 0
    finally:
        temp_file.unlink()

# ==================== Integration Tests ====================

def test_cli_query_prompt_with_content():
    """Test that --query option retrieves prompt when available."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        with patch('main.PROMPTS_FILE', temp_file):
            # We need to re-initialize or mock the prompt_manager used in main
            from main import PromptManager
            mock_manager = PromptManager(temp_file)
            mock_manager.add_prompt("Queued prompt", "test.mp3")
            
            with patch('main.prompt_manager', mock_manager):
                result = runner.invoke(app, ["--query"])
                assert result.exit_code == 0
                assert "Queued prompt" in result.stdout
                assert len(mock_manager.prompts) == 0
    finally:
        temp_file.unlink()

def test_cli_remove_prompt_success():
    """Test that --remove option works with valid index."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        with patch('main.PROMPTS_FILE', temp_file):
            from main import PromptManager
            mock_manager = PromptManager(temp_file)
            mock_manager.add_prompt("Prompt 1", "file1.mp3")
            mock_manager.add_prompt("Prompt 2", "file2.mp3")
            
            with patch('main.prompt_manager', mock_manager):
                result = runner.invoke(app, ["--remove", "1"])
                assert result.exit_code == 0
                assert "Removed prompt 1" in result.stdout
                assert len(mock_manager.prompts) == 1
                assert mock_manager.prompts[0]['prompt'] == "Prompt 2"
    finally:
        temp_file.unlink()

def test_cli_list_prompts_populated():
    """Test that --list option works with populated queue."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        with patch('main.PROMPTS_FILE', temp_file):
            from main import PromptManager
            mock_manager = PromptManager(temp_file)
            mock_manager.add_prompt("List Test", "list.mp3")
            
            with patch('main.prompt_manager', mock_manager):
                result = runner.invoke(app, ["--list"])
                assert result.exit_code == 0
                assert "Stored Prompts:" in result.stdout
                assert "List Test" in result.stdout
    finally:
        temp_file.unlink()

def test_cli_mutually_exclusive_options():
    """Test that --english and --post-process are mutually exclusive."""
    result = runner.invoke(app, ["-e", "-p"])
    assert result.exit_code == 1
    assert "mutually exclusive" in result.stdout

# ==================== PromptManager Unit Tests ====================

def test_promptmanager_remove_prompt_empty():
    """Test PromptManager.remove_prompt with empty queue."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        result = manager.remove_prompt(1)
        assert result is False
        assert len(manager.prompts) == 0
    finally:
        temp_file.unlink()

def test_promptmanager_remove_prompt_invalid_index():
    """Test PromptManager.remove_prompt with invalid index."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        manager.add_prompt("First prompt", "file1.mp3")
        manager.add_prompt("Second prompt", "file2.mp3")
        
        result = manager.remove_prompt(5)
        assert result is False
        assert len(manager.prompts) == 2
    finally:
        temp_file.unlink()

def test_promptmanager_remove_prompt_success():
    """Test PromptManager.remove_prompt removes correct prompt."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = Path(f.name)
    
    try:
        manager = PromptManager(temp_file)
        manager.add_prompt("First prompt", "file1.mp3")
        manager.add_prompt("Second prompt", "file2.mp3")
        manager.add_prompt("Third prompt", "file3.mp3")
        
        result = manager.remove_prompt(2)
        assert result is True
        assert len(manager.prompts) == 2
        assert manager.prompts[0]['prompt'] == "First prompt"
        assert manager.prompts[1]['prompt'] == "Third prompt"
    finally:
        temp_file.unlink()
