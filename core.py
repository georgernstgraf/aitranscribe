import math
import os
import subprocess
from pathlib import Path
from openai import OpenAI

MAX_AUDIO_SIZE_MB = 25


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


def chunk_audio(file_path: str, max_size_mb: int = MAX_AUDIO_SIZE_MB, max_duration_s: int = 600) -> list[str]:
    """Split audio into chunks sized to stay under max_size_mb and max_duration_s.

    Segment length is the smaller of the size-derived value (from the file's
    bitrate, with a 5% margin for keyframe-aligned cut points) and the
    duration-derived value (even split so every chunk is within max_duration_s).
    Files already within both limits are returned unsplit. A file that is
    small but long (e.g. a 43-minute Zoom recording under 25 MB) is still
    split, because STT backends truncate very long single uploads.
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

    _ffmpeg("-i", file_path, "-f", "segment", "-segment_time", str(segment_time), "-c", "copy", out_pattern)

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
    """Transcribes a single audio file, returning (text, detected_language)."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=stt_model,
            file=audio_file,
            response_format="verbose_json"
        )
    language = getattr(transcript, "language", None)
    return str(transcript.text).strip(), language

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
