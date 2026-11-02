"""Live audio fragmentation — the port of polished-recognition's FragmentPreparer.

Two domain terms (canonical glossary in CONTEXT.md):

* **Fragmenttakt** (`cut_interval_s`): the time that must elapse before a cut
  may be placed, measured from the previous *actual* cut. Nothing is analysed
  during that time.
* **Suchfenster** (`search_window_s`): the forward span that must be fully
  recorded before a cut is decided, and that is searched **in full** for the
  quietest place.

The cut is placed at the area centroid of the best silence candidate of the
deficit-area metric Q, clamped 150 ms inside that candidate. Without a
candidate the quietest 10 ms frame is cut (forced cut, Q = 0). Fragments are
gapless: fragment i+1 starts exactly at fragment i's cut, so concatenating all
fragments reproduces the recorded PCM byte for byte.

Deliberate divergence from the original: there is no guard zone / LATE_HALF.
Its rationale there is tied to the seam-stitch decision, which this project
does not have; a pause that straddles the cut-interval boundary stays visible
in the full search window and is preferred.
"""

from __future__ import annotations

import math
import threading
from dataclasses import dataclass
from typing import Callable

import numpy as np

FRAME_MS = 10
HIGHPASS_HZ = 80.0
FLOOR_PERCENTILE = 5.0

DEFAULT_CUT_INTERVAL_S = 45.0
DEFAULT_SEARCH_WINDOW_S = 5.0
DEFAULT_AXIS_K = 0.65
DEFAULT_AXIS_C = 100.0
DEFAULT_MARGIN_MS = 150
DEFAULT_POLL_INTERVAL_S = 0.5


@dataclass(frozen=True)
class CutResult:
    """Where to cut inside a search window and how good that place is."""

    cut_offset_samples: int
    quality: float
    candidate_found: bool
    floor_level: float


@dataclass(frozen=True)
class Fragment:
    """One committed, gapless piece of the recording."""

    index: int
    pcm: np.ndarray
    sample_rate: int
    start_sample: int
    end_sample: int
    silence_aligned: bool
    quality: float

    @property
    def duration_ms(self) -> int:
        return int(round((self.end_sample - self.start_sample) * 1000 / self.sample_rate))


def high_pass(pcm: np.ndarray, sample_rate: int, cutoff_hz: float = HIGHPASS_HZ) -> np.ndarray:
    """One-pole high-pass, deliberately without normalization.

    Normalization would scale the frame levels and therefore move the adaptive
    axis; a scalar gain must never change where the cut lands.
    """
    x = np.asarray(pcm, dtype=np.float64)
    if x.size == 0:
        return x
    rc = 1.0 / (2.0 * math.pi * cutoff_hz)
    dt = 1.0 / float(sample_rate)
    alpha = rc / (rc + dt)
    y = np.empty_like(x)
    prev_x = 0.0
    prev_y = 0.0
    for index in range(x.size):
        current = x[index]
        prev_y = alpha * (prev_y + current - prev_x)
        y[index] = prev_y
        prev_x = current
    return y


def frame_levels(signal: np.ndarray, frame_samples: int) -> np.ndarray:
    """RMS level of every full 10 ms frame."""
    count = signal.size // frame_samples
    if count <= 0:
        return np.empty(0, dtype=np.float64)
    frames = signal[: count * frame_samples].reshape(count, frame_samples)
    return np.sqrt(np.mean(frames * frames, axis=1))


def _candidate_runs(silent: np.ndarray) -> list[tuple[int, int]]:
    """Maximal contiguous runs of True as (start, end-exclusive) pairs."""
    runs: list[tuple[int, int]] = []
    start = None
    for index, flag in enumerate(silent):
        if flag and start is None:
            start = index
        elif not flag and start is not None:
            runs.append((start, index))
            start = None
    if start is not None:
        runs.append((start, len(silent)))
    return runs


def evaluate(
    span: np.ndarray,
    sample_rate: int,
    *,
    axis_k: float = DEFAULT_AXIS_K,
    axis_c: float = DEFAULT_AXIS_C,
    margin_ms: int = DEFAULT_MARGIN_MS,
) -> CutResult | None:
    """Pick the cut point inside one fully recorded search window.

    The metric is the deficit area under the adaptive axis
    ``X = axis_k * mean_level + axis_c``: every frame below X contributes
    ``1 - level/X``, so depth and duration collapse into one number (Q).
    Ties resolve to the earliest candidate; a window without any candidate
    still yields a cut (the quietest frame, Q = 0, forced).
    """
    frame_samples = max(1, int(round(sample_rate * FRAME_MS / 1000)))
    if np.asarray(span).size < frame_samples:
        return None

    levels = frame_levels(high_pass(span, sample_rate), frame_samples)
    if levels.size == 0:
        return None

    mean_level = float(np.mean(levels))
    axis = axis_k * mean_level + axis_c
    floor_level = float(np.percentile(levels, FLOOR_PERCENTILE))
    margin_frames = max(1, int(round(margin_ms / FRAME_MS)))

    if axis <= 0:  # pragma: no cover - axis_c is positive by config
        deficit = np.zeros_like(levels)
    else:
        deficit = np.maximum(0.0, 1.0 - levels / axis)

    candidates = _candidate_runs(levels < axis)
    if not candidates:
        quietest = int(np.argmin(levels))
        return CutResult(
            cut_offset_samples=quietest * frame_samples + frame_samples // 2,
            quality=0.0,
            candidate_found=False,
            floor_level=floor_level,
        )

    best_quality = -1.0
    best_start = best_end = 0
    for start, end in candidates:
        quality = float(np.sum(deficit[start:end]))
        if quality > best_quality:  # strict: ties keep the earliest candidate
            best_quality, best_start, best_end = quality, start, end

    if best_quality <= 0:  # pragma: no cover - a candidate always has deficit > 0
        quietest = int(np.argmin(levels))
        return CutResult(
            cut_offset_samples=quietest * frame_samples + frame_samples // 2,
            quality=0.0,
            candidate_found=False,
            floor_level=floor_level,
        )

    weights = deficit[best_start:best_end]
    indices = np.arange(best_start, best_end, dtype=np.float64)
    centroid = float(np.sum(weights * indices) / best_quality)

    if (best_end - best_start) < 2 * margin_frames:
        cut_frame = int(round((best_start + best_end - 1) / 2.0))
    else:
        low = best_start + margin_frames
        high = best_end - 1 - margin_frames
        cut_frame = int(round(min(max(centroid, low), high)))

    return CutResult(
        cut_offset_samples=cut_frame * frame_samples + frame_samples // 2,
        quality=best_quality,
        candidate_found=True,
        floor_level=floor_level,
    )


class FragmentPreparer:
    """Cuts the live PCM stream into fragments while the recording runs.

    `append()` is called from the audio callback thread, the worker thread
    polls the spool, and every committed fragment is handed to `on_fragment`
    from that worker thread. The spool is trimmed at each cut, so memory stays
    bounded to roughly one fragment plus one search window.
    """

    def __init__(
        self,
        *,
        sample_rate: int = 16000,
        cut_interval_s: float = DEFAULT_CUT_INTERVAL_S,
        search_window_s: float = DEFAULT_SEARCH_WINDOW_S,
        axis_k: float = DEFAULT_AXIS_K,
        axis_c: float = DEFAULT_AXIS_C,
        margin_ms: int = DEFAULT_MARGIN_MS,
        poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
        on_fragment: Callable[[Fragment], None] | None = None,
    ) -> None:
        self.sample_rate = int(sample_rate)
        self.cut_interval_s = float(cut_interval_s)
        self.search_window_s = float(search_window_s)
        self.axis_k = float(axis_k)
        self.axis_c = float(axis_c)
        self.margin_ms = int(margin_ms)
        self.poll_interval_s = float(poll_interval_s)
        self.on_fragment = on_fragment

        self._cut_samples = int(round(self.cut_interval_s * self.sample_rate))
        self._search_samples = int(round(self.search_window_s * self.sample_rate))
        self._lock = threading.Lock()
        self._spool = bytearray()
        self._base_sample = 0  # absolute sample index of spool[0]
        self._next_start = 0  # absolute sample where the next fragment starts
        self._next_index = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: BaseException | None = None
        self._closed = False

    # -- capture side ------------------------------------------------------
    def append(self, pcm: np.ndarray) -> None:
        """Append captured PCM (int16, mono). Safe from the audio callback."""
        arr = np.asarray(pcm)
        if arr.dtype.kind == "f":
            arr = (arr * 32767).astype(np.int16)
        elif arr.dtype != np.int16:
            arr = arr.astype(np.int16)
        if arr.ndim > 1:
            arr = arr[:, 0]
        if arr.size == 0:
            return
        with self._lock:
            if self._closed:
                return
            self._spool.extend(arr.tobytes())

    def pcm_size(self) -> int:
        """Absolute number of samples appended so far."""
        with self._lock:
            return self._base_sample + len(self._spool) // 2

    def _slice(self, start: int, end: int) -> np.ndarray:
        with self._lock:
            low = max(0, (start - self._base_sample) * 2)
            high = max(0, (end - self._base_sample) * 2)
            data = bytes(self._spool[low:high])
        return np.frombuffer(data, dtype=np.int16).copy()

    def _trim(self, up_to: int) -> None:
        with self._lock:
            drop = (up_to - self._base_sample) * 2
            if drop > 0:
                del self._spool[:drop]
                self._base_sample = up_to

    # -- worker ------------------------------------------------------------
    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="aitranscribe-fragmenter", daemon=True
        )
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._encode_available()
            except Exception as exc:  # noqa: BLE001 - surfaced by stop()
                self._error = exc
                return
            self._stop.wait(self.poll_interval_s)

    def stop(self) -> None:
        """Stop the worker thread; raises an error the worker hit, if any."""
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=5)
        if self._error is not None:
            raise self._error

    def _encode_available(self) -> bool:
        """Commit every fragment whose full search window has arrived."""
        committed = False
        while True:
            start = self._next_start
            nominal_end = start + self._cut_samples
            search_end = nominal_end + self._search_samples
            if self.pcm_size() < search_end:
                return committed

            span = self._slice(nominal_end, search_end)
            result = evaluate(
                span,
                self.sample_rate,
                axis_k=self.axis_k,
                axis_c=self.axis_c,
                margin_ms=self.margin_ms,
            )
            if result is None:  # pragma: no cover - window is always >= one frame
                cut, aligned, quality = nominal_end, False, 0.0
            else:
                cut = nominal_end + result.cut_offset_samples
                aligned, quality = result.candidate_found, result.quality
            self._commit(start, cut, aligned, quality)
            committed = True

    def _commit(self, start: int, end: int, aligned: bool, quality: float) -> None:
        pcm = self._slice(start, end)
        fragment = Fragment(
            index=self._next_index,
            pcm=pcm,
            sample_rate=self.sample_rate,
            start_sample=start,
            end_sample=end,
            silence_aligned=aligned,
            quality=quality,
        )
        self._next_index += 1
        self._next_start = end
        self._trim(end)
        if self.on_fragment is not None:
            self.on_fragment(fragment)

    def prepare_tail_sync(self) -> None:
        """Commit everything not yet committed after the capture stopped.

        Any full fragment that became available is committed first; the
        trailing remainder is taken whole and unsearched — no seam follows it.
        """
        self._encode_available()
        start = self._next_start
        total = self.pcm_size()
        self._closed = True
        if total > start:
            self._commit(start, total, aligned=False, quality=0.0)
