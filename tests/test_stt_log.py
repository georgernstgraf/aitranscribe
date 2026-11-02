"""Contracts for the per-request STT log (JSONL, one line per event)."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from stt_log import SttRequestLog, default_log_path, estimate_request_bytes


def read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_request_line_carries_every_field(tmp_path):
    log = SttRequestLog(tmp_path / "stt.jsonl")

    log.request(
        fragment_index=3,
        endpoint_url="https://whisper.test/v1",
        model="large-v3",
        audio_duration_ms=47_500,
        upload_format="none",
        request_bytes=1_520_000,
        duration_ms=2_310,
        silence_aligned=True,
        quality=12.5,
        seam_quality=3.5,
        conditioned=True,
        prompt_chars=42,
        pre_roll_ms=1000,
        echo_trimmed_tokens=2,
    )

    (record,) = read_lines(tmp_path / "stt.jsonl")
    assert record["event"] == "stt_request"
    assert record["fragment"] == 3
    assert record["endpoint"] == "https://whisper.test/v1"
    assert record["model"] == "large-v3"
    assert record["audio_duration_ms"] == 47_500
    assert record["upload_format"] == "none"
    assert record["request_bytes"] == 1_520_000
    assert record["duration_ms"] == 2_310
    assert record["silence_aligned"] is True
    assert record["quality"] == 12.5
    assert record["seam_quality"] == 3.5
    assert record["conditioned"] is True
    assert record["prompt_chars"] == 42
    assert record["pre_roll_ms"] == 1000
    assert record["echo_trimmed_tokens"] == 2
    assert "ts" in record


def test_error_line_keeps_type_and_status(tmp_path):
    log = SttRequestLog(tmp_path / "stt.jsonl")

    log.error(
        fragment_index=1,
        endpoint_url="https://whisper.test/v1",
        model="large-v3",
        error_type="BadRequestError",
        status_code=400,
        message="invalid file format",
    )

    (record,) = read_lines(tmp_path / "stt.jsonl")
    assert record["event"] == "stt_error"
    assert record["error_type"] == "BadRequestError"
    assert record["status_code"] == 400
    assert record["message"] == "invalid file format"


def test_error_line_without_status_code(tmp_path):
    log = SttRequestLog(tmp_path / "stt.jsonl")

    log.error(
        fragment_index=0,
        endpoint_url="https://whisper.test/v1",
        model="large-v3",
        error_type="APIConnectionError",
        message="Name or service not known",
    )

    (record,) = read_lines(tmp_path / "stt.jsonl")
    assert record["status_code"] is None


def test_summary_line_aggregates_the_session(tmp_path):
    log = SttRequestLog(tmp_path / "stt.jsonl")

    log.summary(
        fragments=4,
        audio_ms=180_000,
        request_bytes=6_000_000,
        request_ms=9_500,
        errors=1,
        recording_ms=185_000,
        stop_to_raw_ms=2_200,
    )

    (record,) = read_lines(tmp_path / "stt.jsonl")
    assert record["event"] == "stt_summary"
    assert record["fragments"] == 4
    assert record["errors"] == 1
    assert record["stop_to_raw_ms"] == 2_200


def test_lines_append_across_instances(tmp_path):
    path = tmp_path / "stt.jsonl"
    SttRequestLog(path).error(
        fragment_index=0, endpoint_url="u", model="m", error_type="Timeout"
    )
    SttRequestLog(path).summary(
        fragments=0, audio_ms=0, request_bytes=0, request_ms=0,
        errors=1, recording_ms=0, stop_to_raw_ms=0,
    )

    assert [record["event"] for record in read_lines(path)] == ["stt_error", "stt_summary"]


def test_estimate_request_bytes_counts_file_model_and_prompt(tmp_path):
    audio = tmp_path / "frag.wav"
    audio.write_bytes(b"x" * 1000)

    assert estimate_request_bytes(str(audio), "m", prompt="abc") == 1000 + 1 + 3
    assert estimate_request_bytes(str(tmp_path / "missing.wav"), "m") == 1


def test_default_log_path_lives_under_xdg_state(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert default_log_path() == tmp_path / "aitranscribe" / "stt_requests.jsonl"
