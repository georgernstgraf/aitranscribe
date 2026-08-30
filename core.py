import os
import subprocess
from pathlib import Path
from openai import OpenAI


def _ffmpeg(*args: str) -> None:
    """Run ffmpeg with given arguments. Raises RuntimeError on failure."""
    cmd = ["ffmpeg", "-y", *args]
    result = subprocess.run(cmd, capture_output=True, text=True)
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
    result = subprocess.run(cmd, capture_output=True, text=True)
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
    _ffmpeg("-i", file_path, "-b:a", "32k", output_path)
    return output_path


def chunk_audio(file_path: str, max_size_mb: int = 25) -> list[str]:
    """Split audio into 10-minute chunks for files larger than max_size_mb."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        return [file_path]

    file_name = Path(file_path).stem
    file_ext = Path(file_path).suffix
    output_dir = Path(file_path).parent
    out_pattern = str(output_dir / f"{file_name}_chunk%01d{file_ext}")

    _ffmpeg("-i", file_path, "-f", "segment", "-segment_time", "600", "-c", "copy", out_pattern)

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
