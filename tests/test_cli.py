import pytest
import typer
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock
import tempfile
import os

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
        new_option,
        english_option,
        help_option,
        file_option,
        file_path_argument,
        list_prompts_option,
        query_prompt_option,
        remove_prompt_option,
        get_post_process_prompt,
        cleanup_old_records,
        validate_api_keys,
        wrap_text,
        console,
        CONFIG_FILE,
        stt_client,
        llm_client,
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

def test_new_option():
    """Test that new_option returns correct typer.Option."""
    option = new_option()
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

def test_get_post_process_prompt_english_only():
    """Test English translation prompt."""
    result = get_post_process_prompt(english=True, post_process=False)
    assert result is not None
    assert "Please translate the following text to English" in result
    assert "correct grammatical errors" in result

def test_get_post_process_prompt_post_process_only():
    """Test default post-processing prompt."""
    result = get_post_process_prompt(english=False, post_process=True)
    assert result == "Please correct grammatical errors, remove filler words, and structure the following text."

def test_get_post_process_prompt_none():
    """Test no post-processing."""
    result = get_post_process_prompt(english=False, post_process=False)
    assert result is None

def test_cleanup_old_records():
    """Test that cleanup_old_records deletes matching files."""
    temp_dir = tempfile.mkdtemp()
    
    # Create test files
    test_files = [
        os.path.join(temp_dir, "aitranscribe_record_v01.txt"),
        os.path.join(temp_dir, "aitranscribe_record_v02.txt"),
        os.path.join(temp_dir, "other_file.txt"),
    ]
    
    for f in test_files:
        with open(f, 'w') as fp:
            fp.write("test")
    
    try:
        # Patch tempfile.gettempdir to return our test directory
        with patch('tempfile.gettempdir', return_value=temp_dir):
            # Run cleanup
            deleted_count = cleanup_old_records()
            
            # Check that only aitranscribe_record files were deleted
            assert deleted_count == 2
            assert not os.path.exists(test_files[0])
            assert not os.path.exists(test_files[1])
            assert os.path.exists(test_files[2])  # Other files should remain
    finally:
        # Cleanup remaining test files
        for f in test_files:
            if os.path.exists(f):
                os.remove(f)
        os.rmdir(temp_dir)

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
    """Test PromptManager.query_prompt retrieves and removes oldest prompt."""
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
