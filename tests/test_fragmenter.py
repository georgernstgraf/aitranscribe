"""Behavioral contracts for the live fragmenter (port of polished-recognition).

Ported from the original's SilenceQualityTest / FragmentPreparerTest: the cut
lands inside the quietest candidate, the stream stays gapless, the cut interval
and the search window are respected, and the tail is taken whole.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fragmenter import (
    DEFAULT_AXIS_C,
    DEFAULT_AXIS_K,
    FRAME_MS,
    FragmentPreparer,
    evaluate,
    frame_levels,
    high_pass,
)

SR = 16000
FRAME = SR * FRAME_MS // 1000  # 160 samples


def speech(seconds: float, amplitude: int = 6000, freq: float = 180.0) -> np.ndarray:
    t = np.arange(int(seconds * SR)) / SR
    return (amplitude * np.sin(2 * np.pi * freq * t)).astype(np.int16)


def silence(seconds: float, amplitude: int = 0) -> np.ndarray:
    return np.full(int(seconds * SR), amplitude, dtype=np.int16)


def burst_train(pause_seconds: float = 0.6, speech_seconds: float = 3.0, repeats: int = 20) -> np.ndarray:
    parts = []
    for _ in range(repeats):
        parts.append(speech(speech_seconds))
        parts.append(silence(pause_seconds))
    return np.concatenate(parts)


# --------------------------------------------------------------------------- #
# SilenceQuality: cut placement
# --------------------------------------------------------------------------- #
def test_cut_lands_inside_a_clear_pause():
    span = np.concatenate([speech(1.0), silence(1.0), speech(1.0)])

    result = evaluate(span, SR)

    assert result is not None
    assert result.candidate_found is True
    assert result.quality > 0
    cut_s = result.cut_offset_samples / SR
    # The pause runs 1.0 s .. 2.0 s; the 150 ms margin keeps the cut inside.
    assert 1.15 <= cut_s <= 1.85


def test_cut_never_sits_at_the_candidate_edge():
    """The margin is the real cut-safety guarantee (not a guard zone)."""
    span = np.concatenate([speech(0.5), silence(2.0), speech(0.5)])

    result = evaluate(span, SR, margin_ms=150)

    cut_s = result.cut_offset_samples / SR
    assert 0.65 <= cut_s <= 2.35


def test_short_candidate_is_cut_at_its_midpoint():
    """A candidate shorter than 2 x margin has no room for the clamp."""
    span = np.concatenate([speech(0.5), silence(0.2), speech(0.5)])

    result = evaluate(span, SR, margin_ms=150)

    assert result.candidate_found is True
    cut_s = result.cut_offset_samples / SR
    assert 0.55 <= cut_s <= 0.75


def test_continuous_speech_forces_a_cut_at_the_quietest_frame():
    """No candidate -> best-effort cut, Q = 0, tagged as forced."""
    # A quieter stretch that still sits above the adaptive axis: no candidate.
    span = np.concatenate([
        speech(1.0, amplitude=6000),
        speech(0.2, amplitude=4500),
        speech(1.0, amplitude=6000),
    ])

    result = evaluate(span, SR)

    assert result is not None
    assert result.candidate_found is False
    assert result.quality == 0.0
    cut_s = result.cut_offset_samples / SR
    assert 1.0 <= cut_s <= 1.2


def test_a_single_quiet_dip_is_a_candidate_not_a_forced_cut():
    """Even a 10 ms dip below the axis counts as a (weak) candidate."""
    span = speech(2.0, amplitude=6000).copy()
    quiet_at = int(1.0 * SR)
    span[quiet_at:quiet_at + FRAME] = 400

    result = evaluate(span, SR)

    assert result.candidate_found is True
    assert result.quality > 0
    assert abs(result.cut_offset_samples - (quiet_at + FRAME // 2)) <= FRAME


def test_earliest_candidate_wins_on_a_tie():
    """Two identical pauses: determinism keeps the earlier one."""
    span = np.concatenate([speech(0.5), silence(0.6), speech(0.5), silence(0.6), speech(0.5)])

    result = evaluate(span, SR)

    cut_s = result.cut_offset_samples / SR
    assert cut_s < 1.6  # inside the first pause (0.5 .. 1.1 s)


def test_gain_scaling_does_not_move_the_cut():
    """The axis adapts to the signal level; a louder take cuts at the same place."""
    span = np.concatenate([speech(1.0, amplitude=5000), silence(1.0), speech(1.0, amplitude=5000)])
    louder = (span.astype(np.float64) * 1.5).astype(np.int16)

    quiet_cut = evaluate(span, SR).cut_offset_samples
    loud_cut = evaluate(louder, SR).cut_offset_samples

    assert abs(quiet_cut - loud_cut) <= FRAME


def test_span_shorter_than_one_frame_returns_none():
    assert evaluate(np.zeros(FRAME - 1, dtype=np.int16), SR) is None


def test_floor_level_is_reported_as_evidence():
    span = np.concatenate([speech(1.0), silence(1.0), speech(1.0)])

    result = evaluate(span, SR)

    assert result.floor_level >= 0
    assert result.floor_level < 100  # the P5 floor of a span with a real pause


def test_high_pass_removes_dc_offset():
    dc = np.full(SR, 1000, dtype=np.int16)

    filtered = high_pass(dc, SR)

    assert abs(float(np.mean(filtered[100:]))) < 1.0


def test_frame_levels_are_rms_per_10ms_frame():
    levels = frame_levels(np.full(FRAME * 3, 1000, dtype=np.float64), FRAME)

    assert levels.shape == (3,)
    assert np.allclose(levels, 1000.0)


# --------------------------------------------------------------------------- #
# FragmentPreparer: gapless stream, cut interval, search window, tail
# --------------------------------------------------------------------------- #
def _prepare(pcm: np.ndarray, **kwargs) -> list:
    fragments: list = []
    preparer = FragmentPreparer(sample_rate=SR, on_fragment=fragments.append, **kwargs)
    preparer.append(pcm)
    preparer._encode_available()
    preparer.prepare_tail_sync()
    return fragments


def test_fragments_are_gapless_and_reconstruct_the_recording():
    pcm = burst_train(repeats=8)

    fragments = _prepare(pcm, cut_interval_s=3.0, search_window_s=1.0)

    assert len(fragments) >= 2
    rebuilt = np.concatenate([fragment.pcm for fragment in fragments])
    assert np.array_equal(rebuilt, pcm)
    for previous, current in zip(fragments, fragments[1:]):
        assert current.start_sample == previous.end_sample


def test_every_fragment_respects_cut_interval_and_search_window():
    pcm = burst_train(repeats=10)
    cut_interval_s, search_window_s = 3.0, 1.0

    fragments = _prepare(pcm, cut_interval_s=cut_interval_s, search_window_s=search_window_s)

    for fragment in fragments[:-1]:  # the tail is the remainder, not a cut
        assert fragment.duration_ms >= cut_interval_s * 1000
        assert fragment.duration_ms <= (cut_interval_s + search_window_s) * 1000 + FRAME_MS


def test_no_fragment_is_committed_before_the_full_search_window_arrived():
    cut_interval_s, search_window_s = 2.0, 1.0
    pcm = speech(cut_interval_s + search_window_s - 0.2)  # 0.2 s short of the window
    fragments: list = []
    preparer = FragmentPreparer(
        sample_rate=SR,
        cut_interval_s=cut_interval_s,
        search_window_s=search_window_s,
        on_fragment=fragments.append,
    )

    preparer.append(pcm)
    preparer._encode_available()

    assert fragments == []


def test_tail_is_taken_whole_and_unsearched():
    cut_interval_s = 2.0
    pcm = burst_train(repeats=2)  # 7.2 s: one full fragment plus a remainder
    fragments = _prepare(pcm, cut_interval_s=cut_interval_s, search_window_s=1.0)

    tail = fragments[-1]
    assert tail.silence_aligned is False
    assert tail.quality == 0.0
    assert tail.end_sample == len(pcm)
    assert tail.duration_ms < cut_interval_s * 1000


def test_cut_lands_in_a_pause_of_the_search_window():
    """A pause that straddles the cut-interval boundary stays visible."""
    cut_interval_s, search_window_s = 2.0, 1.0
    # 1.8 s speech, a 1.0 s pause that straddles the 2.0 s boundary, then speech.
    pcm = np.concatenate([speech(1.8), silence(1.0), speech(2.0)])
    fragments = _prepare(pcm, cut_interval_s=cut_interval_s, search_window_s=search_window_s)

    first = fragments[0]
    assert first.silence_aligned is True
    # The pause runs 1.8 .. 2.8 s; the cut must sit inside it.
    assert 1.8 * SR <= first.end_sample <= 2.8 * SR


def test_spool_is_trimmed_after_each_commit():
    pcm = burst_train(repeats=6)
    preparer = FragmentPreparer(
        sample_rate=SR, cut_interval_s=3.0, search_window_s=1.0, on_fragment=lambda _f: None
    )
    preparer.append(pcm)

    preparer._encode_available()

    # Everything before the last cut is gone; only the remainder plus window stays.
    assert preparer.pcm_size() == len(pcm)
    assert len(preparer._spool) // 2 <= 4 * SR


def test_worker_thread_commits_fragments_while_audio_arrives():
    import time

    fragments: list = []
    preparer = FragmentPreparer(
        sample_rate=SR,
        cut_interval_s=1.0,
        search_window_s=0.5,
        poll_interval_s=0.01,
        on_fragment=fragments.append,
    )
    preparer.start()
    try:
        pcm = burst_train(repeats=3)
        for offset in range(0, len(pcm), SR // 10):
            preparer.append(pcm[offset:offset + SR // 10])
            time.sleep(0.001)
        deadline = time.time() + 5
        while len(fragments) < 2 and time.time() < deadline:
            time.sleep(0.01)
    finally:
        preparer.stop()
    preparer.prepare_tail_sync()

    assert len(fragments) >= 2
    rebuilt = np.concatenate([fragment.pcm for fragment in fragments])
    assert np.array_equal(rebuilt, pcm)


def test_worker_error_is_raised_by_stop(monkeypatch):
    preparer = FragmentPreparer(sample_rate=SR, poll_interval_s=0.01)

    def boom():
        raise RuntimeError("analysis failed")

    monkeypatch.setattr(preparer, "_encode_available", boom)
    preparer.start()
    import time
    deadline = time.time() + 5
    while preparer._error is None and time.time() < deadline:
        time.sleep(0.01)

    with pytest.raises(RuntimeError, match="analysis failed"):
        preparer.stop()


def test_defaults_match_the_agreed_start_values():
    preparer = FragmentPreparer()

    assert preparer.cut_interval_s == 45.0
    assert preparer.search_window_s == 5.0
    assert preparer.axis_k == DEFAULT_AXIS_K
    assert preparer.axis_c == DEFAULT_AXIS_C
