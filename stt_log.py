"""One-line-per-request STT logging (JSONL).

Every fragment request writes exactly one line, every API error its own line,
and the stop tap closes the session with a summary line. The log is append-only
JSONL so it can be tailed, grepped and analysed without a schema migration.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path


def default_log_path() -> Path:
    """`$XDG_STATE_HOME/aitranscribe/stt_requests.jsonl` (falls back to ~/.local/state)."""
    state_home = os.environ.get("XDG_STATE_HOME") or str(Path.home() / ".local" / "state")
    return Path(state_home) / "aitranscribe" / "stt_requests.jsonl"


def estimate_request_bytes(file_path: str, model: str, prompt: str = "") -> int:
    """Payload size of one transcription request (file + model + prompt).

    HTTP headers and multipart boundaries are not included; the number is the
    audio bytes plus the textual parameters, which is what the log needs to
    compare requests against each other.
    """
    try:
        audio_bytes = os.path.getsize(file_path)
    except OSError:
        audio_bytes = 0
    return audio_bytes + len(model.encode("utf-8")) + len(prompt.encode("utf-8"))


class SttRequestLog:
    """Thread-safe JSONL writer for the per-fragment STT log."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else default_log_path()
        self._lock = threading.Lock()

    def _write(self, record: dict) -> None:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            **record,
        }
        line = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def request(
        self,
        *,
        fragment_index: int,
        endpoint_url: str,
        model: str,
        audio_duration_ms: int,
        upload_format: str,
        request_bytes: int,
        duration_ms: int,
        silence_aligned: bool,
        quality: float,
    ) -> None:
        """One successfully answered fragment request."""
        self._write(
            {
                "event": "stt_request",
                "fragment": fragment_index,
                "endpoint": endpoint_url,
                "model": model,
                "audio_duration_ms": audio_duration_ms,
                "upload_format": upload_format,
                "request_bytes": request_bytes,
                "duration_ms": duration_ms,
                "silence_aligned": silence_aligned,
                "quality": round(float(quality), 3),
            }
        )

    def error(
        self,
        *,
        fragment_index: int,
        endpoint_url: str,
        model: str,
        error_type: str,
        status_code: int | None = None,
        message: str = "",
    ) -> None:
        """Any failed request: DNS/host errors, 4xx, 5xx, timeouts, …"""
        self._write(
            {
                "event": "stt_error",
                "fragment": fragment_index,
                "endpoint": endpoint_url,
                "model": model,
                "error_type": error_type,
                "status_code": status_code,
                "message": message,
            }
        )

    def summary(
        self,
        *,
        fragments: int,
        audio_ms: int,
        request_bytes: int,
        request_ms: int,
        errors: int,
        recording_ms: int,
        stop_to_raw_ms: int,
    ) -> None:
        """The stop-tap summary line."""
        self._write(
            {
                "event": "stt_summary",
                "fragments": fragments,
                "audio_ms": audio_ms,
                "request_bytes": request_bytes,
                "request_ms": request_ms,
                "errors": errors,
                "recording_ms": recording_ms,
                "stop_to_raw_ms": stop_to_raw_ms,
            }
        )
