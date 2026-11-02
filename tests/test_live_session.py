"""Contracts for the live session: serial order, partial text, logging, archive."""

import json
import sys
import types
import wave
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import config
import fragmenter
import main

SR = main.RECORDING_SAMPLE_RATE


def speech(seconds: float, amplitude: int = 6000) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (amplitude * np.sin(2 * np.pi * 180 * t)).astype(np.int16)


def burst_train(repeats: int = 4) -> np.ndarray:
    parts = []
    for _ in range(repeats):
        parts.append(speech(0.8))
        parts.append(np.zeros(int(0.5 * SR), dtype=np.int16))
    return np.concatenate(parts)


def make_session(
    monkeypatch, tmp_path, *, upload_format="none", seam_quality_min=10.0
):
    monkeypatch.setattr(
        main,
        "CONFIG",
        types.SimpleNamespace(
            recording=config.RecordingSettings(
                cut_interval_s=1.0,
                search_window_s=0.5,
                seam_quality_min=seam_quality_min,
            )
        ),
    )
    monkeypatch.setattr(
        main,
        "STT_ENDPOINT",
        types.SimpleNamespace(base_url="https://whisper.test/v1", upload_format=upload_format),
    )
    monkeypatch.setattr(main, "require_stt_client", lambda: None)
    session = main.LiveTranscriptionSession(
        settings={"stt_model": "large-v3"},
        log_path=tmp_path / "stt.jsonl",
    )
    session.fragmenter.poll_interval_s = 0.01
    return session


def feed(session, pcm, chunk_samples=SR // 10):
    for offset in range(0, len(pcm), chunk_samples):
        session.add_audio(pcm[offset:offset + chunk_samples])


def read_log(tmp_path) -> list[dict]:
    path = tmp_path / "stt.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_fragments_are_transcribed_serially_and_joined_in_order(monkeypatch, tmp_path):
    calls: list[str] = []

    def fake_transcribe(client, path, model, **kwargs):
        calls.append(path)
        return f"f{len(calls) - 1}", "de"

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train())
    raw = session.finish()

    assert len(calls) >= 2
    assert raw == " ".join(f"f{index}" for index in range(len(calls)))
    assert session.detected_language == "de"
    session.cleanup()


def test_partial_text_grows_with_every_committed_fragment(monkeypatch, tmp_path):
    partials: list[str] = []

    def fake_transcribe(client, path, model, **kwargs):
        return f"part{len(partials)}", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)
    session.on_partial_text = partials.append

    session.start()
    feed(session, burst_train())
    raw = session.finish()

    assert len(partials) >= 2
    assert partials[-1] == raw
    for earlier, later in zip(partials, partials[1:]):
        assert later.startswith(earlier)
    session.cleanup()


def test_every_fragment_writes_one_log_line_and_a_summary(monkeypatch, tmp_path):
    def fake_transcribe(client, path, model, **kwargs):
        return "text", "de"

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train())
    session.finish()
    session.cleanup()

    records = read_log(tmp_path)
    requests = [record for record in records if record["event"] == "stt_request"]
    summaries = [record for record in records if record["event"] == "stt_summary"]

    assert len(requests) >= 2
    assert len(summaries) == 1
    for record in requests:
        assert record["endpoint"] == "https://whisper.test/v1"
        assert record["model"] == "large-v3"
        assert record["audio_duration_ms"] > 0
        assert record["upload_format"] == "none"
        assert record["request_bytes"] > 0
        assert record["duration_ms"] >= 0

    summary = summaries[0]
    assert summary["fragments"] == len(requests)
    assert summary["errors"] == 0
    assert summary["audio_ms"] > 0
    assert summary["request_bytes"] > 0
    assert summary["stop_to_raw_ms"] >= 0


def test_a_failed_fragment_is_logged_and_partial_text_is_delivered(monkeypatch, tmp_path):
    calls = {"count": 0}

    def flaky_transcribe(client, path, model, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("upstream 500")
        return f"survivor{calls['count']}", None

    monkeypatch.setattr(main, "transcribe_audio", flaky_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train())
    raw = session.finish()
    session.cleanup()

    records = read_log(tmp_path)
    errors = [record for record in records if record["event"] == "stt_error"]
    summary = [record for record in records if record["event"] == "stt_summary"][0]

    assert len(errors) == 1
    assert errors[0]["error_type"] == "RuntimeError"
    assert "upstream 500" in errors[0]["message"]
    assert summary["errors"] == 1
    requests = [record for record in records if record["event"] == "stt_request"]
    assert raw == " ".join(f"survivor{index}" for index in range(2, calls["count"] + 1))


def test_a_completely_failed_session_raises(monkeypatch, tmp_path):
    def broken_transcribe(client, path, model, **kwargs):
        raise ConnectionError("host not found")

    monkeypatch.setattr(main, "transcribe_audio", broken_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train())
    with pytest.raises(ConnectionError, match="host not found"):
        session.finish()
    session.cleanup()

    errors = [record for record in read_log(tmp_path) if record["event"] == "stt_error"]
    assert errors
    assert errors[0]["status_code"] is None


def test_upload_format_comes_from_the_endpoint_profile(monkeypatch, tmp_path):
    formats: list[str] = []

    def fake_encode(pcm, sample_rate, output_path, upload_format="none"):
        formats.append(upload_format)
        target = str(Path(output_path).with_suffix(".mp3"))
        Path(target).write_bytes(b"encoded")
        return target

    monkeypatch.setattr(main, "encode_fragment", fake_encode)
    monkeypatch.setattr(main, "transcribe_audio", lambda client, path, model, **kwargs: ("text", None))
    session = make_session(monkeypatch, tmp_path, upload_format="mp3")

    session.start()
    feed(session, burst_train())
    session.finish()
    session.cleanup()

    assert formats
    assert set(formats) == {"mp3"}


def test_archive_mp3_encodes_the_full_recording(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "transcribe_audio", lambda client, path, model, **kwargs: ("text", None))
    session = make_session(monkeypatch, tmp_path)
    pcm = burst_train()
    target = tmp_path / "archive.mp3"

    def fake_compress(source, output_path=None):
        with wave.open(source, "rb") as handle:
            frames = handle.readframes(handle.getnframes())
        Path(output_path).write_bytes(frames)
        return output_path

    monkeypatch.setattr(main, "compress_audio", fake_compress)

    session.start()
    feed(session, pcm)
    session.finish()
    result = session.write_archive_mp3(str(target))
    session.cleanup()

    assert result == str(target)
    assert target.read_bytes() == pcm.tobytes()


def test_abort_removes_the_working_directory(monkeypatch, tmp_path):
    session = make_session(monkeypatch, tmp_path)
    work_dir = Path(session._work_dir)
    session.start()

    session.abort()

    assert not work_dir.exists()


def test_cleanup_is_idempotent(monkeypatch, tmp_path):
    session = make_session(monkeypatch, tmp_path)
    session.start()
    session.abort()

    session.cleanup()  # must not raise


# --------------------------------------------------------------------------- #
# Seam conditioning (pre-roll, prompt carry-over, echo trim)
# --------------------------------------------------------------------------- #
def test_second_fragment_upload_carries_one_second_of_pre_roll(monkeypatch, tmp_path):
    lengths: list[int] = []

    def fake_encode(pcm, sample_rate, output_path, upload_format="none"):
        lengths.append(len(pcm))
        target = str(Path(output_path).with_suffix(".wav"))
        Path(target).write_bytes(b"x")
        return target

    monkeypatch.setattr(main, "encode_fragment", fake_encode)
    monkeypatch.setattr(
        main, "transcribe_audio", lambda client, path, model, **kwargs: ("text", None)
    )
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, speech(4.0))  # continuous tone: every cut is forced (Q = 0)
    session.finish()
    session.cleanup()

    records = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert len(records) >= 2
    assert lengths[0] == round(records[0]["audio_duration_ms"] * SR / 1000)
    for length, record in zip(lengths[1:], records[1:]):
        expected = record["audio_duration_ms"] * SR / 1000 + SR  # + 1 s pre-roll
        assert abs(length - expected) <= 32


def test_prompt_carry_over_uses_the_previous_transcript(monkeypatch, tmp_path):
    prompts: list[str | None] = []

    def fake_transcribe(client, path, model, prompt=None, on_prompt_rejected=None):
        prompts.append(prompt)
        return f"fragment{len(prompts) - 1} text", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, speech(4.0))  # forced cuts, so every seam is conditioned
    session.finish()
    session.cleanup()

    assert len(prompts) >= 2
    assert prompts[0] is None
    assert prompts[1] == "fragment0 text"
    assert all(prompt is not None for prompt in prompts[1:])


def test_echo_trim_removes_the_repeated_seam_words(monkeypatch, tmp_path):
    def fake_transcribe(client, path, model, **kwargs):
        return "und den Schnitt Danach geht es weiter.", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, speech(4.0))  # forced cuts, so every seam is conditioned
    raw = session.finish()
    session.cleanup()

    assert raw.count("Danach") == 1


def test_rejected_prompt_disables_prompts_for_the_session(monkeypatch, tmp_path):
    prompts: list[str | None] = []

    def fake_transcribe(client, path, model, prompt=None, on_prompt_rejected=None):
        prompts.append(prompt)
        if prompt is not None and on_prompt_rejected is not None:
            on_prompt_rejected()
        return f"text{len(prompts)}", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, speech(4.0))  # forced cuts, so every seam is conditioned
    session.finish()
    session.cleanup()

    assert len(prompts) >= 3
    assert prompts[0] is None
    assert prompts[1] is not None
    assert all(prompt is None for prompt in prompts[2:])


def test_log_records_the_gate_and_the_conditioning(monkeypatch, tmp_path):
    def fake_transcribe(client, path, model, **kwargs):
        return "ein Text", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, speech(4.0))  # forced cuts, so every seam is conditioned
    session.finish()
    session.cleanup()

    records = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert records[0]["seam_quality"] == 0
    assert records[0]["conditioned"] is False
    assert records[0]["prompt_chars"] == 0
    assert records[0]["pre_roll_ms"] == 0
    assert records[1]["seam_quality"] == records[0]["quality"] == 0
    assert records[1]["conditioned"] is True
    assert records[1]["prompt_chars"] > 0
    assert records[1]["pre_roll_ms"] == 1000
    # "ein Text" repeats the previous tail, so the echo trim ate both tokens.
    assert records[1]["echo_trimmed_tokens"] == 2


# --------------------------------------------------------------------------- #
# Q-gate: condition a seam only below seam_quality_min
# --------------------------------------------------------------------------- #
def test_a_pause_aligned_seam_stays_bare(monkeypatch, tmp_path):
    lengths: list[int] = []

    def fake_encode(pcm, sample_rate, output_path, upload_format="none"):
        lengths.append(len(pcm))
        target = str(Path(output_path).with_suffix(".wav"))
        Path(target).write_bytes(b"x")
        return target

    monkeypatch.setattr(main, "encode_fragment", fake_encode)
    monkeypatch.setattr(
        main, "transcribe_audio", lambda client, path, model, **kwargs: ("ein Text", None)
    )
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train())  # 0.5 s pauses: high Q, well above the gate
    session.finish()
    session.cleanup()

    records = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert len(records) >= 2
    for record in records[1:]:
        assert record["seam_quality"] >= 10
        assert record["conditioned"] is False
        assert record["pre_roll_ms"] == 0
        assert record["prompt_chars"] == 0
        assert record["echo_trimmed_tokens"] == 0
    for length, record in zip(lengths[1:], records[1:]):
        # the upload is the bare fragment, no pre-roll
        assert length == round(record["audio_duration_ms"] * SR / 1000)


def test_a_forced_cut_conditions_the_seam(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main, "transcribe_audio", lambda client, path, model, **kwargs: ("ein Text", None)
    )
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, speech(4.0))  # continuous tone: forced cuts, Q = 0
    session.finish()
    session.cleanup()

    records = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert len(records) >= 2
    for record in records[1:]:
        assert record["seam_quality"] == 0
        assert record["conditioned"] is True
        assert record["pre_roll_ms"] == 1000
        assert record["prompt_chars"] > 0


def test_a_bare_seam_keeps_a_real_repetition(monkeypatch, tmp_path):
    def fake_transcribe(client, path, model, **kwargs):
        return "sehr sehr gut", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train())  # bare seams: no pre-roll, so no echo to trim
    raw = session.finish()
    session.cleanup()

    requests = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert raw.count("sehr sehr gut") == len(requests)
    assert all(record["echo_trimmed_tokens"] == 0 for record in requests)


def test_the_rest_fragment_inherits_the_predecessors_seam_quality(monkeypatch, tmp_path):
    monkeypatch.setattr(
        main, "transcribe_audio", lambda client, path, model, **kwargs: ("ein Text", None)
    )
    session = make_session(monkeypatch, tmp_path)

    session.start()
    feed(session, burst_train(repeats=2))  # one pause-aligned cut plus a tail
    session.finish()
    session.cleanup()

    records = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert len(records) == 2
    assert records[0]["quality"] > 0
    assert records[1]["quality"] == 0  # the tail has no end cut of its own
    assert records[1]["seam_quality"] == records[0]["quality"]
    assert records[1]["conditioned"] is False


def test_seam_quality_min_zero_never_conditions(monkeypatch, tmp_path):
    prompts: list[str | None] = []

    def fake_transcribe(client, path, model, prompt=None, on_prompt_rejected=None):
        prompts.append(prompt)
        return "ein Text", None

    monkeypatch.setattr(main, "transcribe_audio", fake_transcribe)
    session = make_session(monkeypatch, tmp_path, seam_quality_min=0.0)

    session.start()
    feed(session, speech(4.0))  # forced cuts, but the gate is off
    session.finish()
    session.cleanup()

    requests = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert len(requests) >= 2
    assert all(record["conditioned"] is False for record in requests)
    assert all(prompt is None for prompt in prompts)


def test_a_small_positive_seam_quality_is_conditioned(monkeypatch, tmp_path):
    def fake_encode(pcm, sample_rate, output_path, upload_format="none"):
        target = str(Path(output_path).with_suffix(".wav"))
        Path(target).write_bytes(b"x")
        return target

    monkeypatch.setattr(main, "encode_fragment", fake_encode)
    monkeypatch.setattr(
        main, "transcribe_audio", lambda client, path, model, **kwargs: ("ein Text", None)
    )
    session = make_session(monkeypatch, tmp_path)
    pcm = speech(0.2)

    def fragment(index: int, quality: float) -> fragmenter.Fragment:
        start = index * len(pcm)
        return fragmenter.Fragment(
            index=index,
            pcm=pcm,
            sample_rate=SR,
            start_sample=start,
            end_sample=start + len(pcm),
            quality=quality,
        )

    session.start()
    session._queue.put(fragment(0, 250.0))  # pause-aligned end cut
    session._queue.put(fragment(1, 5.0))    # weak candidate, below the gate
    session._queue.put(fragment(2, 0.0))    # forced cut
    session.finish()
    session.cleanup()

    records = [record for record in read_log(tmp_path) if record["event"] == "stt_request"]
    assert [record["seam_quality"] for record in records] == [0, 250.0, 5.0]
    assert [record["conditioned"] for record in records] == [False, False, True]
