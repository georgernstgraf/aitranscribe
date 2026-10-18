import math
import os
import re
import subprocess
from pathlib import Path
from openai import BadRequestError, OpenAI

MAX_AUDIO_SIZE_MB = 25

# Groq assembles the transcript of long uploads incorrectly: from the first
# non-ASCII character of a word it drops the rest of that span, so German
# umlaut words come back cut ("würde" -> "w", "natürlich" -> "nat", "möchte"
# -> "m") and whole spans can disappear. The `words[]` array stays correct and
# uploads at or below ~120 s are unaffected. Measured 2026-10-18: <=120 s clean,
# >=122 s mangled, both whisper-large-v3 and -turbo, no request parameter avoids
# it. Two defences: cap uploads here and rebuild the text from `words[]` in
# transcribe_audio(). See docs/ai/PITFALLS.md.
GROQ_MAX_UPLOAD_S = 120

# Chunk cut points are snapped into detected pauses: a cut inside a word makes
# Whisper emit that word's fragment, which is the same visible damage as the
# Groq bug above.
_SILENCE_NOISE_DB = 35
_SILENCE_MIN_S = 0.25
_SILENCE_SNAP_MAX_S = 30.0
_SILENCE_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_SILENCE_END_RE = re.compile(r"silence_end:\s*(-?[\d.]+)")


def _ffmpeg(*args: str) -> None:
    """Run ffmpeg with given arguments. Raises RuntimeError on failure."""
    cmd = ["ffmpeg", "-y", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg is required for audio processing; install FFmpeg and restart the terminal.") from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (exit {result.returncode}): {result.stderr.strip()}"
        )


def _ffprobe(file_path: str) -> dict[str, str]:
    """Get format info from ffprobe as a dict of key=value lines."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "compact=p=0:nk=1",
        file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("ffprobe is required for audio processing; install FFmpeg and restart the terminal.") from exc
    if result.returncode != 0:
        raise RuntimeError(
            f"ffprobe failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    return {"duration": result.stdout.strip()}


def get_audio_duration(file_path: str) -> float:
    """Return the duration of the audio file in seconds via ffprobe."""
    info = _ffprobe(file_path)
    return float(info["duration"])


def compress_audio(file_path: str, output_path: str | None = None) -> str:
    """Compress audio to MP3 via ffmpeg."""
    if output_path is None:
        file_name = Path(file_path).stem
        output_dir = Path(file_path).parent
        output_path = str(output_dir / f"{file_name}_compressed.mp3")
    _ffmpeg("-i", file_path, "-map", "0:a:0", "-vn", "-b:a", "32k", output_path)
    if not os.path.isfile(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(
            f"ffmpeg reported success but produced no output: {output_path}"
        )
    return output_path


def _parse_silence_midpoints(stderr: str) -> list[float]:
    """Midpoints (seconds) of the silence intervals in ffmpeg silencedetect output."""
    midpoints: list[float] = []
    pending_start: float | None = None
    for line in stderr.splitlines():
        start_match = _SILENCE_START_RE.search(line)
        if start_match:
            pending_start = float(start_match.group(1))
            continue
        end_match = _SILENCE_END_RE.search(line)
        if end_match and pending_start is not None:
            midpoints.append((pending_start + float(end_match.group(1))) / 2)
            pending_start = None
    return midpoints


def _silence_midpoints(file_path: str) -> list[float]:
    """Silence midpoints via ffmpeg silencedetect, [] when detection is unavailable.

    Best-effort by design: an unreadable file, a missing ffmpeg or an stderr
    without silence markers only costs cut quality (nominal cut points), never
    the chunking itself.
    """
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", file_path, "-vn",
        "-af", f"silencedetect=noise=-{_SILENCE_NOISE_DB}dB:d={_SILENCE_MIN_S}",
        "-f", "null", "-",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
    except FileNotFoundError:
        return []
    return _parse_silence_midpoints(result.stderr)


def _snap_cut_points(duration: float, segment_time: int, midpoints: list[float]) -> list[int]:
    """Cut points every `segment_time` seconds, moved into the nearest pause.

    Each nominal cut point is moved to the closest silence midpoint within
    ``min(_SILENCE_SNAP_MAX_S, 35% of segment_time)``; without a nearby
    midpoint the nominal position is kept. The result is strictly increasing
    and inside the file, so `ffmpeg -f segment -segment_times` gets valid input.
    """
    margin = min(_SILENCE_SNAP_MAX_S, segment_time * 0.35)
    cuts: list[int] = []
    for index in range(1, math.ceil(duration / segment_time)):
        nominal = index * segment_time
        previous = cuts[-1] if cuts else 0
        candidates = [
            point
            for point in midpoints
            if previous + 1 < point < duration and abs(point - nominal) <= margin
        ]
        nearest = min(candidates, key=lambda point: abs(point - nominal)) if candidates else nominal
        cuts.append(int(round(nearest)))
    return cuts


def chunk_audio(file_path: str, max_size_mb: int = MAX_AUDIO_SIZE_MB, max_duration_s: int = GROQ_MAX_UPLOAD_S) -> list[str]:
    """Split audio into chunks sized to stay under max_size_mb and max_duration_s.

    Segment length is the smaller of the size-derived value (from the file's
    bitrate, with a 5% margin for keyframe-aligned cut points) and the
    duration-derived value (even split so every chunk is within max_duration_s,
    which defaults to the Groq upload ceiling). Cut points are snapped into
    detected pauses so a seam cannot split a word. Files already within both
    limits are returned unsplit. A file that is small but long (e.g. a
    43-minute Zoom recording under 25 MB) is still split, because STT backends
    truncate very long single uploads.
    """
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    try:
        duration = get_audio_duration(file_path)
    except Exception as exc:
        if file_size_mb <= max_size_mb:
            return [file_path]
        raise RuntimeError(f"Cannot determine audio duration for {file_path}: {exc}") from exc
    if file_size_mb <= max_size_mb and (duration <= 0 or duration <= max_duration_s):
        return [file_path]

    if duration <= 0:
        raise RuntimeError(
            f"Cannot chunk audio: invalid duration ({duration}s) for {file_path}"
        )
    rate_mb_per_s = file_size_mb / duration
    size_based = int((max_size_mb / rate_mb_per_s) * 0.95)
    num_chunks = max(1, math.ceil(duration / max_duration_s))
    duration_based = math.ceil(duration / num_chunks)
    segment_time = max(60, min(size_based, duration_based))

    file_name = Path(file_path).stem
    file_ext = Path(file_path).suffix
    output_dir = Path(file_path).parent
    out_pattern = str(output_dir / f"{file_name}_chunk%01d{file_ext}")

    cut_points = _snap_cut_points(duration, segment_time, _silence_midpoints(file_path))
    if cut_points:
        segment_args = ("-segment_times", ",".join(str(cut) for cut in cut_points))
    else:
        # No cut point fits (e.g. a file over the size limit but shorter than the
        # segment floor): keep the classic single cut, which ffmpeg answers with
        # one chunk.
        segment_args = ("-segment_time", str(segment_time))
    _ffmpeg("-i", file_path, "-f", "segment", *segment_args, "-c", "copy", out_pattern)

    chunks: list[str] = []
    i = 0
    while True:
        chunk_path = str(output_dir / f"{file_name}_chunk{i}{file_ext}")
        if os.path.exists(chunk_path):
            chunks.append(chunk_path)
            i += 1
        else:
            break

    if not chunks:
        chunks.append(file_path)

    return chunks

def transcribe_audio(client: OpenAI, file_path: str, stt_model: str) -> tuple[str, str | None]:
    """Transcribes a single audio file, returning (text, detected_language).

    The transcript is rebuilt from the word-level timestamps when the service
    returns them: on uploads longer than ~120 s Groq drops everything from a
    word's first non-ASCII character onwards in `text`/`segments[].text`, while
    `words[]` stays correct — see docs/ai/PITFALLS.md. Without word timestamps
    (models that reject the parameter) the plain `text` is used; the
    GROQ_MAX_UPLOAD_S upload cap keeps that path correct too.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    with open(file_path, "rb") as audio_file:
        request = {
            "model": stt_model,
            "file": audio_file,
            "response_format": "verbose_json",
        }
        try:
            transcript = client.audio.transcriptions.create(
                **request, timestamp_granularities=["word"]
            )
        except BadRequestError:
            audio_file.seek(0)
            transcript = client.audio.transcriptions.create(**request)
    language = getattr(transcript, "language", None)
    words = getattr(transcript, "words", None) or []
    text = " ".join(word.word for word in words) if words else str(transcript.text)
    return text.strip(), language

def process_with_llm(client: OpenAI, messages: list[dict], llm_model: str) -> str:
    """Sends pre-built messages to an LLM and returns the response content."""
    response = client.chat.completions.create(
        model=llm_model,
        messages=messages
    )
    if not response.choices:
        raise RuntimeError(f"LLM returned no choices (model: {llm_model})")
    content = response.choices[0].message.content
    return (content or "").strip()
