import pytest
from unittest.mock import patch, MagicMock, mock_open
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    _ffmpeg,
    _ffprobe,
    get_audio_duration,
    compress_audio,
    chunk_audio,
    transcribe_audio,
    process_with_llm,
)


def _run_result(returncode=0, stdout="", stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


# --- _ffmpeg ---

def test_ffmpeg_success_does_not_raise():
    with patch("core.subprocess.run", return_value=_run_result(0)) as mock_run:
        _ffmpeg("-i", "in.wav", "out.mp3")
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "ffmpeg"
    assert cmd[1] == "-y"
    assert cmd[-2:] == ["in.wav", "out.mp3"]

def test_ffmpeg_failure_raises_runtime_error_with_stderr():
    with patch("core.subprocess.run", return_value=_run_result(1, stderr="  bad option  ")):
        with pytest.raises(RuntimeError) as exc_info:
            _ffmpeg("-i", "in.wav")
    assert "exit 1" in exc_info.value.args[0]
    assert "bad option" in exc_info.value.args[0]

# --- _ffprobe ---

def test_ffprobe_returns_duration_dict():
    with patch("core.subprocess.run", return_value=_run_result(0, stdout="12.5\n")) as mock_run:
        info = _ffprobe("file.mp3")
    assert info == {"duration": "12.5"}
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "ffprobe"
    assert "file.mp3" in cmd

def test_ffprobe_failure_raises_runtime_error_with_stderr():
    with patch("core.subprocess.run", return_value=_run_result(2, stderr="no such file")):
        with pytest.raises(RuntimeError) as exc_info:
            _ffprobe("missing.mp3")
    assert "exit 2" in exc_info.value.args[0]
    assert "no such file" in exc_info.value.args[0]

# --- get_audio_duration ---

def test_get_audio_duration_parses_ffprobe_output():
    with patch("core._ffprobe", return_value={"duration": "12.5"}):
        assert get_audio_duration("file.mp3") == 12.5

# --- compress_audio ---

def test_compress_audio_default_output_path(tmp_path):
    src = tmp_path / "recording.wav"
    src.write_bytes(b"x")
    with patch("core._ffmpeg") as mock_ffmpeg:
        out = compress_audio(str(src))
    assert out == str(tmp_path / "recording_compressed.mp3")
    mock_ffmpeg.assert_called_once_with("-i", str(src), "-b:a", "32k", out)

def test_compress_audio_explicit_output_path(tmp_path):
    src = tmp_path / "recording.wav"
    src.write_bytes(b"x")
    explicit = str(tmp_path / "custom.mp3")
    with patch("core._ffmpeg") as mock_ffmpeg:
        out = compress_audio(str(src), output_path=explicit)
    assert out == explicit
    mock_ffmpeg.assert_called_once_with("-i", str(src), "-b:a", "32k", explicit)

# --- chunk_audio ---

def test_chunk_audio_small_file_passthrough(tmp_path):
    src = tmp_path / "small.mp3"
    src.write_bytes(b"x")
    with patch("core._ffmpeg") as mock_ffmpeg:
        assert chunk_audio(str(src)) == [str(src)]
    mock_ffmpeg.assert_not_called()

def test_chunk_audio_large_file_creates_chunks(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    created = [tmp_path / "big_chunk0.mp3", tmp_path / "big_chunk1.mp3"]

    def fake_ffmpeg(*args):
        for chunk in created:
            chunk.write_bytes(b"c")

    with patch("core._ffmpeg", side_effect=fake_ffmpeg) as mock_ffmpeg:
        chunks = chunk_audio(str(src), max_size_mb=0)

    mock_ffmpeg.assert_called_once()
    args = mock_ffmpeg.call_args.args
    out_pattern = args[-1]
    assert out_pattern == str(tmp_path / "big_chunk%01d.mp3")
    assert "-f" in args and "segment" in args
    assert args[args.index("-segment_time") + 1] == "600"
    assert "-c" in args and "copy" in args
    assert chunks == [str(c) for c in created]

def test_chunk_audio_no_chunks_created_falls_back_to_source(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    with patch("core._ffmpeg"):
        chunks = chunk_audio(str(src), max_size_mb=0)
    assert chunks == [str(src)]

# --- transcribe_audio ---

def test_transcribe_audio_calls_client_and_strips(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()
    captured = {}
    verbose = MagicMock()
    verbose.text = "  hello world  "
    verbose.language = "german"

    def capture(**kwargs):
        captured.update(kwargs)
        captured["file_bytes"] = kwargs["file"].read()
        return verbose

    client.audio.transcriptions.create.side_effect = capture
    assert transcribe_audio(client, str(src), "whisper-large-v3-turbo") == ("hello world", "german")
    assert captured["model"] == "whisper-large-v3-turbo"
    assert captured["response_format"] == "verbose_json"
    assert captured["file_bytes"] == b"audio-bytes"
    assert captured["file"].closed


def test_transcribe_audio_handles_missing_language(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()
    verbose = MagicMock(spec=["text"])
    verbose.text = "hello"
    client.audio.transcriptions.create.return_value = verbose
    assert transcribe_audio(client, str(src), "m") == ("hello", None)

# --- process_with_llm (moved from test_cli.py) ---

def _mock_llm_response(choices, content=None):
    response = MagicMock()
    response.choices = choices
    if choices:
        response.choices[0].message.content = content
    return response

def test_process_with_llm_strips_content():
    """Test that process_with_llm strips whitespace from returned content."""
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_llm_response(
        [MagicMock()], content="  hello world  "
    )
    assert process_with_llm(client, [{"role": "user", "content": "hi"}], "m") == "hello world"

def test_process_with_llm_none_content_returns_empty():
    """Test that process_with_llm returns empty string when content is None."""
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_llm_response(
        [MagicMock()], content=None
    )
    assert process_with_llm(client, [], "m") == ""

def test_process_with_llm_zero_choices_raises():
    """Test that process_with_llm raises RuntimeError when the API returns zero choices."""
    client = MagicMock()
    client.chat.completions.create.return_value = _mock_llm_response([])
    with pytest.raises(RuntimeError) as exc_info:
        process_with_llm(client, [], "test-model")
    assert "no choices" in exc_info.value.args[0]
    assert "test-model" in exc_info.value.args[0]
