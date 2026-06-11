import os
from pathlib import Path
from openai import OpenAI
from pydub import AudioSegment

def get_audio_duration(file_path: str) -> float:
    """Return the duration of the audio file in seconds."""
    audio = AudioSegment.from_file(file_path)
    return len(audio) / 1000.0

def compress_audio(file_path: str, output_path: str | None = None) -> str:
    """Compress WAV to MP3 via ffmpeg. Raises if ffmpeg is not available."""
    audio = AudioSegment.from_file(file_path)
    if output_path is None:
        file_name = Path(file_path).stem
        output_dir = Path(file_path).parent
        output_path = str(output_dir / f"{file_name}_compressed.mp3")
    audio.export(output_path, format="mp3", bitrate="32k")
    return output_path

def chunk_audio(file_path: str, max_size_mb: int = 25) -> list[str]:
    """Split audio into chunks < max_size_mb. Falls back to whole file if ffmpeg is missing."""
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb <= max_size_mb:
        return [file_path]

    audio = AudioSegment.from_file(file_path)

    chunk_length_ms = 10 * 60 * 1000  # 10 minutes
    chunks = []

    file_name = Path(file_path).stem
    file_ext = Path(file_path).suffix
    output_dir = Path(file_path).parent

    for i, chunk_start in enumerate(range(0, len(audio), chunk_length_ms)):
        chunk = audio[chunk_start:chunk_start + chunk_length_ms]
        chunk_path = output_dir / f"{file_name}_chunk{i}{file_ext}"
        chunk.export(str(chunk_path), format=file_ext.strip("."))
        chunks.append(str(chunk_path))

    return chunks

def transcribe_audio(client: OpenAI, file_path: str, stt_model: str) -> str:
    """Transcribes a single audio file using the provided client and model."""
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model=stt_model,
            file=audio_file,
            response_format="text"
        )
    return str(transcript).strip()

def process_with_llm(client: OpenAI, messages: list[dict], llm_model: str) -> str:
    """Sends pre-built messages to an LLM and returns the response content."""
    response = client.chat.completions.create(
        model=llm_model,
        messages=messages
    )
    content = response.choices[0].message.content
    return content.strip() if content else ""
