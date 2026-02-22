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
        file_path_argument,
        update_interval_option,
        apply_english_translation,
        cleanup_old_records,
        validate_api_keys,
        console,
        CONFIG_FILE,
        stt_client,
        llm_client,
    )
except ImportError as e:
    pytest.fail(f"Failed to import the CLI app due to missing dependencies: {e}")

runner = CliRunner()

def test_cli_help():
    """Test that the CLI loads and the help command works."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "aitranscribe" in result.stdout
    assert "file" in result.stdout
    assert "record" in result.stdout

def test_cli_file_missing_arg():
    """Test that the file command defaults to /tmp/aitranscribe_record.mp3."""
    result = runner.invoke(app, ["file"])
    # Should fail because the default file does not exist in testing
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

def test_update_interval_option():
    """Test that update_interval_option returns correct typer.Option."""
    option = update_interval_option()
    assert isinstance(option, typer.models.OptionInfo)


# ==================== Logic Helper Tests ====================

def test_apply_english_translation_with_existing_prompt():
    """Test that English translation is appended to existing prompt."""
    existing_prompt = "Fix the grammar."
    result = apply_english_translation(existing_prompt)
    assert result is not None
    assert "Please translate the following text to English" in result
    assert "Fix the grammar." in result

def test_apply_english_translation_without_existing_prompt():
    """Test that English translation prompt is created when none exists."""
    result = apply_english_translation(None)
    assert result is not None
    assert "Please translate the following text to English" in result
    assert "correct grammatical errors" in result
    assert "remove filler words" in result
    assert "structure it clearly" in result

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


# ==================== Integration Tests ====================

def test_record_command_help():
    """Test that record command help works after refactoring."""
    result = runner.invoke(app, ["record", "--help"])
    assert result.exit_code == 0
    assert "Record audio from the microphone" in result.stdout
    assert "--english" in result.stdout
    assert "--verbose" in result.stdout
    assert "--new" in result.stdout

def test_file_command_help():
    """Test that file command help works after refactoring."""
    result = runner.invoke(app, ["file", "--help"])
    assert result.exit_code == 0
    assert "Transcribe a local audio or video file" in result.stdout
    assert "--english" in result.stdout
    assert "--verbose" in result.stdout
    assert "--new" in result.stdout
