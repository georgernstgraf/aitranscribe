import pytest
from unittest.mock import patch, MagicMock, mock_open
import os

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import (
    _ffmpeg,
    _ffprobe,
    _parse_silence_midpoints,
    _silence_midpoints,
    _snap_cut_points,
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

def test_ffmpeg_missing_reports_installation_requirement():
    with patch("core.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="ffmpeg is required"):
            _ffmpeg("-i", "in.wav", "out.mp3")

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

def test_ffprobe_missing_reports_installation_requirement():
    with patch("core.subprocess.run", side_effect=FileNotFoundError):
        with pytest.raises(RuntimeError, match="ffprobe is required"):
            _ffprobe("file.mp3")

# --- get_audio_duration ---

def test_get_audio_duration_parses_ffprobe_output():
    with patch("core._ffprobe", return_value={"duration": "12.5"}):
        assert get_audio_duration("file.mp3") == 12.5

# --- compress_audio ---

def test_compress_audio_default_output_path(tmp_path):
    src = tmp_path / "recording.wav"
    src.write_bytes(b"x")
    expected = tmp_path / "recording_compressed.mp3"
    with patch("core._ffmpeg") as mock_ffmpeg:
        expected.write_bytes(b"audio")
        out = compress_audio(str(src))
    assert out == str(expected)
    mock_ffmpeg.assert_called_once_with("-i", str(src), "-map", "0:a:0", "-vn", "-b:a", "32k", out)

def test_compress_audio_explicit_output_path(tmp_path):
    src = tmp_path / "recording.wav"
    src.write_bytes(b"x")
    explicit = tmp_path / "custom.mp3"
    with patch("core._ffmpeg") as mock_ffmpeg:
        explicit.write_bytes(b"audio")
        out = compress_audio(str(src), output_path=str(explicit))
    assert out == str(explicit)
    mock_ffmpeg.assert_called_once_with("-i", str(src), "-map", "0:a:0", "-vn", "-b:a", "32k", str(explicit))

def test_compress_audio_missing_output_raises(tmp_path):
    src = tmp_path / "recording.wav"
    src.write_bytes(b"x")
    missing = tmp_path / "never_created.mp3"
    with patch("core._ffmpeg"):
        with pytest.raises(RuntimeError) as exc_info:
            compress_audio(str(src), output_path=str(missing))
    assert "produced no output" in exc_info.value.args[0]
    assert str(missing) in exc_info.value.args[0]

def test_compress_audio_empty_output_raises(tmp_path):
    src = tmp_path / "recording.wav"
    src.write_bytes(b"x")
    empty = tmp_path / "empty.mp3"
    empty.write_bytes(b"")
    with patch("core._ffmpeg"):
        with pytest.raises(RuntimeError) as exc_info:
            compress_audio(str(src), output_path=str(empty))
    assert "produced no output" in exc_info.value.args[0]

# --- chunk_audio ---

def segment_cuts(mock_ffmpeg) -> list[str]:
    """Cut points handed to `ffmpeg -f segment` (explicit times or a fixed length)."""
    args = mock_ffmpeg.call_args.args
    if "-segment_times" in args:
        return args[args.index("-segment_times") + 1].split(",")
    return [args[args.index("-segment_time") + 1]]


def test_parse_silence_midpoints_pairs_start_and_end():
    stderr = (
        "[silencedetect @ 0x1] silence_start: 12.5\n"
        "[silencedetect @ 0x1] silence_end: 15.5 | silence_duration: 3\n"
        "[silencedetect @ 0x1] silence_start: 60\n"
        "[silencedetect @ 0x1] silence_end: 64 | silence_duration: 4\n"
    )
    assert _parse_silence_midpoints(stderr) == [14.0, 62.0]


def test_parse_silence_midpoints_ignores_unpaired_start():
    assert _parse_silence_midpoints("[silencedetect @ 0x1] silence_start: 5\n") == []


def test_silence_midpoints_returns_empty_without_ffmpeg(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"x")
    with patch("core.subprocess.run", side_effect=FileNotFoundError):
        assert _silence_midpoints(str(src)) == []


def test_silence_midpoints_parses_ffmpeg_stderr(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"x")
    stderr = (
        "[silencedetect @ 0x1] silence_start: 1\n"
        "[silencedetect @ 0x1] silence_end: 3 | silence_duration: 2\n"
    )
    with patch("core.subprocess.run", return_value=_run_result(0, stderr=stderr)) as mock_run:
        assert _silence_midpoints(str(src)) == [2.0]
    cmd = mock_run.call_args.args[0]
    assert cmd[0] == "ffmpeg"
    assert any("silencedetect" in str(part) for part in cmd)


def test_snap_cut_points_moves_into_nearest_pause():
    # Nominal cuts at 60/120/180; pauses at 63.2 s and 175.0 s are within reach.
    assert _snap_cut_points(240.0, 60, [63.2, 175.0, 400.0]) == [63, 120, 175]


def test_snap_cut_points_keeps_nominal_without_nearby_pause():
    # 90 s away from the nominal positions and beyond the file end are ignored.
    assert _snap_cut_points(240.0, 60, [150.0, 300.0]) == [60, 120, 180]


def test_snap_cut_points_stays_strictly_increasing():
    # A pause before an earlier cut must not push a later cut backwards.
    cuts = _snap_cut_points(300.0, 60, [58.0, 61.0, 118.0])
    assert cuts == sorted(set(cuts))
    assert all(cut < 300 for cut in cuts)


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

    with patch("core.get_audio_duration", return_value=1200.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg", side_effect=fake_ffmpeg) as mock_ffmpeg:
        chunks = chunk_audio(str(src), max_size_mb=0)

    mock_ffmpeg.assert_called_once()
    args = mock_ffmpeg.call_args.args
    out_pattern = args[-1]
    assert out_pattern == str(tmp_path / "big_chunk%01d.mp3")
    assert "-f" in args and "segment" in args
    assert segment_cuts(mock_ffmpeg)[0] == "60"
    assert "-c" in args and "copy" in args
    assert chunks == [str(c) for c in created]

def test_chunk_audio_no_chunks_created_falls_back_to_source(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    with patch("core.get_audio_duration", return_value=1200.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg"):
        chunks = chunk_audio(str(src), max_size_mb=0)
    assert chunks == [str(src)]

def test_chunk_audio_segment_time_derived_from_bitrate(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    # 285 MB over 1200s -> 25 MB max = 100s * 0.95 margin -> 100s (beats the cap
    # and the 60s floor).
    with patch("core.os.path.getsize", return_value=285 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=1200.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg") as mock_ffmpeg:
        chunk_audio(str(src), max_size_mb=25)
    assert segment_cuts(mock_ffmpeg)[0] == "100"

def test_chunk_audio_segment_time_floored_at_60s(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    # 100 MB over 60s -> 25 MB max = 15s * 0.95 = 14s -> floored to 60s
    with patch("core.os.path.getsize", return_value=100 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=60.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg") as mock_ffmpeg:
        chunk_audio(str(src), max_size_mb=25)
    assert segment_cuts(mock_ffmpeg)[0] == "60"

def test_chunk_audio_invalid_duration_raises(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    with patch("core.os.path.getsize", return_value=50 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=0.0), \
         patch("core._ffmpeg") as mock_ffmpeg:
        with pytest.raises(RuntimeError) as exc_info:
            chunk_audio(str(src), max_size_mb=25)
    assert "invalid duration" in exc_info.value.args[0]
    assert str(src) in exc_info.value.args[0]
    mock_ffmpeg.assert_not_called()

def test_chunk_audio_large_file_preserves_probe_failure(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    with patch("core.os.path.getsize", return_value=50 * 1024 * 1024), \
         patch("core.get_audio_duration", side_effect=RuntimeError("ffprobe is required")):
        with pytest.raises(RuntimeError, match="ffprobe is required"):
            chunk_audio(str(src))

def test_chunk_audio_small_but_long_file_splits_by_duration(tmp_path):
    src = tmp_path / "meeting.m4a"
    src.write_bytes(b"x")
    # 1 MB over 2569s (43 min): under the size limit, but over the 120s cap.
    # 2569 / ceil(2569/120)=22 -> 117s segments (size-derived value is far larger).
    with patch("core.os.path.getsize", return_value=1 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=2569.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg") as mock_ffmpeg:
        chunk_audio(str(src))
    assert segment_cuts(mock_ffmpeg)[0] == "117"

def test_chunk_audio_ceil_prevents_tiny_extra_chunk(tmp_path):
    src = tmp_path / "interview.mp3"
    src.write_bytes(b"x")
    # 601s / ceil(601/120)=6 -> 101s segments; truncating instead would leave a
    # tiny 7th chunk.
    with patch("core.os.path.getsize", return_value=9 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=601.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg") as mock_ffmpeg:
        chunk_audio(str(src))
    cuts = segment_cuts(mock_ffmpeg)
    assert cuts[0] == "101"
    assert len(cuts) == 5

def test_chunk_audio_duration_limit_wins_over_size_limit(tmp_path):
    src = tmp_path / "big.mp3"
    src.write_bytes(b"x")
    # 50 MB over 1200s: size-derived 570s, duration-derived 1200/10=120s -> 120s.
    with patch("core.os.path.getsize", return_value=50 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=1200.0), \
         patch("core._silence_midpoints", return_value=[]), \
         patch("core._ffmpeg") as mock_ffmpeg:
        chunk_audio(str(src), max_size_mb=25)
    assert segment_cuts(mock_ffmpeg)[0] == "120"

def test_chunk_audio_cuts_are_snapped_into_pauses(tmp_path):
    src = tmp_path / "meeting.mp3"
    src.write_bytes(b"x")
    with patch("core.os.path.getsize", return_value=1 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=360.0), \
         patch("core._silence_midpoints", return_value=[119.0, 400.0]), \
         patch("core._ffmpeg") as mock_ffmpeg:
        chunk_audio(str(src))
    # 120s segments: the 120s cut moves into the pause at 119s, the 240s cut has
    # no pause within the snap margin (and 400s is beyond the file) so it stays.
    assert segment_cuts(mock_ffmpeg) == ["119", "240"]

def test_chunk_audio_within_both_limits_passthrough(tmp_path):
    src = tmp_path / "short.mp3"
    src.write_bytes(b"x")
    with patch("core.os.path.getsize", return_value=5 * 1024 * 1024), \
         patch("core.get_audio_duration", return_value=120.0), \
         patch("core._ffmpeg") as mock_ffmpeg:
        assert chunk_audio(str(src)) == [str(src)]
    mock_ffmpeg.assert_not_called()

# --- transcribe_audio ---

def test_transcribe_audio_calls_client_and_strips(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()
    captured = {}
    verbose = MagicMock()
    verbose.text = "  hello world  "
    verbose.words = None
    verbose.language = "german"

    def capture(**kwargs):
        captured.update(kwargs)
        captured["file_bytes"] = kwargs["file"].read()
        return verbose

    client.audio.transcriptions.create.side_effect = capture
    assert transcribe_audio(client, str(src), "whisper-large-v3-turbo") == ("hello world", "german")
    assert captured["model"] == "whisper-large-v3-turbo"
    assert captured["response_format"] == "verbose_json"
    assert captured["timestamp_granularities"] == ["word"]
    assert captured["file_bytes"] == b"audio-bytes"
    assert captured["file"].closed


def test_transcribe_audio_rebuilds_text_from_word_timestamps(tmp_path):
    """Groq cuts the `text` of long uploads at the first non-ASCII character.

    Regression guard: the transcript must come from `words[]`, which stays
    correct, so umlaut words survive (docs/ai/PITFALLS.md).
    """
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()
    verbose = MagicMock()
    verbose.text = " Bitte f Sie die M zum Gru"          # mangled by the service
    verbose.language = "german"
    verbose.words = [
        MagicMock(word=word)
        for word in ["Bitte", "führen", "Sie", "die", "Mühle", "zum", "Grüßen"]
    ]
    client.audio.transcriptions.create.return_value = verbose

    text, language = transcribe_audio(client, str(src), "whisper-large-v3")

    assert text == "Bitte führen Sie die Mühle zum Grüßen"
    assert language == "german"


def test_transcribe_audio_uses_text_when_words_are_missing(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()
    verbose = MagicMock()
    verbose.text = " Thank you. "
    verbose.words = []
    verbose.language = None
    client.audio.transcriptions.create.return_value = verbose

    assert transcribe_audio(client, str(src), "whisper-large-v3") == ("Thank you.", None)


def test_transcribe_audio_retries_without_word_timestamps_on_rejection(tmp_path):
    """Models without word timestamps must still transcribe (text path)."""
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()

    class _RejectsWordTimestamps(Exception):
        pass

    verbose = MagicMock()
    verbose.text = "hello"
    verbose.words = None
    verbose.language = None
    client.audio.transcriptions.create.side_effect = [_RejectsWordTimestamps(), verbose]

    with patch("core.BadRequestError", _RejectsWordTimestamps):
        assert transcribe_audio(client, str(src), "distil-whisper") == ("hello", None)

    calls = client.audio.transcriptions.create.call_args_list
    assert len(calls) == 2
    assert calls[0].kwargs["timestamp_granularities"] == ["word"]
    assert "timestamp_granularities" not in calls[1].kwargs
    assert calls[1].kwargs["response_format"] == "verbose_json"


def test_transcribe_audio_handles_missing_language(tmp_path):
    src = tmp_path / "audio.mp3"
    src.write_bytes(b"audio-bytes")
    client = MagicMock()
    verbose = MagicMock(spec=["text"])
    verbose.text = "hello"
    client.audio.transcriptions.create.return_value = verbose
    assert transcribe_audio(client, str(src), "m") == ("hello", None)

def test_transcribe_audio_missing_file_raises(tmp_path):
    client = MagicMock()
    missing = str(tmp_path / "nonexistent.mp3")
    with pytest.raises(FileNotFoundError) as exc_info:
        transcribe_audio(client, missing, "whisper-large-v3-turbo")
    assert missing in exc_info.value.args[0]
    client.audio.transcriptions.create.assert_not_called()

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
