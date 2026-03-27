import sys
import time
import os
import re
import shutil
import typer
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
import sqlite3
import datetime
from pathlib import Path
from typing import Any, Callable
from rich.console import Console
from rich.progress import Progress, TextColumn
from dotenv import dotenv_values, load_dotenv, set_key
from openai import OpenAI
from pynput import keyboard
from core import chunk_audio, transcribe_audio, process_with_llm, compress_audio

console = Console(highlight=False, color_system=None)
state = {"verbose": False}

PRE_PROCESS_MODES = {
    "raw": {
        "label": "Raw transcription",
        "prompt": None,
    },
    "cleanup": {
        "label": "Cleanup Text / Preserve Language",
        "prompt": "Please correct grammatical errors, remove filler words, and structure the following text clearly.",
    },
    "english": {
        "label": "Cleanup + Translate to English",
        "prompt": "Please translate the following text to English, correct grammatical errors, remove filler words, and structure it clearly.",
    },
}

SUMMARY_PROMPT = (
    "Create a concise summary of the transcription in 70 to 80 characters. "
    "Output only the summary text with no quotes, labels, or extra commentary."
)

LLM_PROVIDERS = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "env_model": "OPENROUTER_LLM_MODEL",
        "default_model": "anthropic/claude-3-haiku",
    },
    "cohere": {
        "base_url": "https://api.cohere.ai/compatibility/v1",
        "env_key": "COHERE_API_KEY",
        "env_model": "COHERE_LLM_MODEL",
        "default_model": "command-r",
    },
    "z.ai": {
        "base_url": "https://api.z.ai/api/coding/paas/v4",
        "env_key": "ZAI_API_KEY",
        "env_model": "ZAI_LLM_MODEL",
        "default_model": "glm-5",
    },
}

if os.name == 'nt':
    appdata = os.getenv('APPDATA')
    if appdata:
        CONFIG_DIR = Path(appdata) / "aitranscribe"
    else:
        CONFIG_DIR = Path.home() / "AppData" / "Roaming" / "aitranscribe"
else:
    CONFIG_DIR = Path.home() / ".config" / "aitranscribe"

CONFIG_FILE = CONFIG_DIR / "config"
PROMPTS_FILE = CONFIG_DIR / "prompts.sqlite"

def _create_default_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write('# Speech-to-Text Configuration\n')
        f.write('GROQ_API_KEY="your_groq_api_key_here"\n')
        f.write('GROQ_STT_MODEL="whisper-large-v3-turbo"\n')
        f.write('\n# LLM Post-Processing Configuration\n')
        f.write('LLM_PROVIDER="openrouter"\n')
        f.write('\n# OpenRouter (default provider)\n')
        f.write('OPENROUTER_API_KEY="your_openrouter_api_key_here"\n')
        f.write('OPENROUTER_LLM_MODEL="anthropic/claude-3-haiku"\n')
        f.write('\n# Cohere (alternative provider)\n')
        f.write('# COHERE_API_KEY="your_cohere_api_key_here"\n')
        f.write('# COHERE_LLM_MODEL="command-r"\n')
        f.write('\n# z.ai (alternative provider)\n')
        f.write('# ZAI_API_KEY="your_zai_api_key_here"\n')
        f.write('# ZAI_LLM_MODEL="glm-5"\n')
        f.write('\n# TUI Defaults\n')
        f.write('PRE_PROCESS_MODE="english"\n')
        f.write('TRANSCRIBE_SOURCE="microphone"\n')
        f.write('LAST_FILE_PATH=""\n')
        f.write('VERBOSE_ERRORS="false"\n')
        f.write(f'\nPROMPTS_FILE="{PROMPTS_FILE}"\n')
    console.print(f"Created configuration at {CONFIG_FILE}")
    console.print("Please edit this file to add your API keys before running the tool.")

def _migrate_config() -> None:
    config_text = CONFIG_FILE.read_text()
    if "GROQ_API_KEY" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('\n# Added during migration\n')
            f.write('GROQ_API_KEY="your_groq_api_key_here"\n')
            f.write('GROQ_STT_MODEL="whisper-large-v3-turbo"\n')
    if "LLM_PROVIDER" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('\n# Added during multi-provider migration\n')
            f.write('LLM_PROVIDER="openrouter"\n')
    if "COHERE_API_KEY" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('\n# Cohere (alternative provider)\n')
            f.write('# COHERE_API_KEY="your_cohere_api_key_here"\n')
            f.write('# COHERE_LLM_MODEL="command-r"\n')
    if "ZAI_API_KEY" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('\n# z.ai (alternative provider)\n')
            f.write('# ZAI_API_KEY="your_zai_api_key_here"\n')
            f.write('# ZAI_LLM_MODEL="glm-5"\n')
    if "PRE_PROCESS_MODE" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('\n# TUI Defaults\n')
            f.write('PRE_PROCESS_MODE="english"\n')
    if "TRANSCRIBE_SOURCE" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('TRANSCRIBE_SOURCE="microphone"\n')
    if "LAST_FILE_PATH" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('LAST_FILE_PATH=""\n')
    if "VERBOSE_ERRORS" not in config_text:
        with open(CONFIG_FILE, "a") as f:
            f.write('VERBOSE_ERRORS="false"\n')

if not CONFIG_FILE.exists():
    _create_default_config()
else:
    _migrate_config()

load_dotenv(dotenv_path=CONFIG_FILE)

PROMPTS_FILE = Path(os.getenv("PROMPTS_FILE", str(PROMPTS_FILE)))

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openrouter").lower()


def _env_flag(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_pre_process_mode(value: str | None) -> str:
    normalized = (value or "english").strip().lower()
    return normalized if normalized in PRE_PROCESS_MODES else "english"


DEFAULT_PRE_PROCESS_MODE = _normalize_pre_process_mode(os.getenv("PRE_PROCESS_MODE", "english"))
DEFAULT_VERBOSE_ERRORS = _env_flag("VERBOSE_ERRORS", False)


def _normalize_transcribe_source(value: str | None) -> str:
    normalized = (value or "microphone").strip().lower()
    return normalized if normalized in {"microphone", "file"} else "microphone"

def _get_llm_client() -> OpenAI | None:
    if LLM_PROVIDER not in LLM_PROVIDERS:
        console.print(f"Warning: Unknown LLM_PROVIDER '{LLM_PROVIDER}', falling back to 'openrouter'")
        provider = LLM_PROVIDERS["openrouter"]
    else:
        provider = LLM_PROVIDERS[LLM_PROVIDER]

    api_key = os.getenv(provider["env_key"])
    if not api_key or api_key == f"your_{LLM_PROVIDER}_api_key_here":
        return None

    return OpenAI(
        base_url=provider["base_url"],
        api_key=api_key,
    )

def _get_llm_model() -> str:
    if LLM_PROVIDER not in LLM_PROVIDERS:
        provider = LLM_PROVIDERS["openrouter"]
    else:
        provider = LLM_PROVIDERS[LLM_PROVIDER]
    return os.getenv(provider["env_model"], provider["default_model"])


def persist_config_value(key: str, value: str, *, config_file: Path = CONFIG_FILE) -> None:
    config_file.parent.mkdir(parents=True, exist_ok=True)
    set_key(str(config_file), key, value, quote_mode="auto")
    os.environ[key] = value


def persist_tui_setting(setting_name: str, value: Any) -> None:
    if setting_name == "pre_process_mode":
        persist_config_value("PRE_PROCESS_MODE", _normalize_pre_process_mode(str(value)))
        return
    if setting_name == "input_source":
        persist_config_value("TRANSCRIBE_SOURCE", _normalize_transcribe_source(str(value)))
        return
    if setting_name == "file_path":
        persist_config_value("LAST_FILE_PATH", str(value).strip())
        return
    if setting_name == "verbose":
        persist_config_value("VERBOSE_ERRORS", "true" if bool(value) else "false")
        return
    if setting_name == "stt_model":
        persist_config_value("GROQ_STT_MODEL", str(value).strip() or GROQ_STT_MODEL)
        return
    if setting_name == "llm_model":
        provider = LLM_PROVIDERS.get(LLM_PROVIDER, LLM_PROVIDERS["openrouter"])
        persist_config_value(provider["env_model"], str(value).strip() or provider["default_model"])


def get_tui_settings() -> dict[str, Any]:
    config = dotenv_values(CONFIG_FILE)
    provider = LLM_PROVIDERS.get(LLM_PROVIDER, LLM_PROVIDERS["openrouter"])
    return {
        "pre_process_mode": _normalize_pre_process_mode(config.get("PRE_PROCESS_MODE") or DEFAULT_PRE_PROCESS_MODE),
        "input_source": _normalize_transcribe_source(config.get("TRANSCRIBE_SOURCE")),
        "file_path": str(config.get("LAST_FILE_PATH") or "").strip(),
        "stt_model": (config.get("GROQ_STT_MODEL") or GROQ_STT_MODEL or "whisper-large-v3-turbo").strip(),
        "llm_model": (config.get(provider["env_model"]) or LLM_MODEL or provider["default_model"]).strip(),
        "verbose": str(config.get("VERBOSE_ERRORS", str(DEFAULT_VERBOSE_ERRORS))).strip().lower() in {"1", "true", "yes", "on"},
    }

stt_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
) if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here" else None

llm_client = _get_llm_client()
LLM_MODEL = _get_llm_model()

# Option Factory Functions
def post_process_option():
    return typer.Option(False, "--post-process", "-p", help="Refine text: correct grammar, remove fillers, and structure clearly")

def stt_model_option():
    return typer.Option(GROQ_STT_MODEL, help="Groq STT model to use")

def llm_model_option():
    return typer.Option(LLM_MODEL, "--llm-model", "-m", help="LLM model to use for post-processing")

def verbose_option():
    return typer.Option(False, "--verbose", "-v", help="Show verbose error outputs")

def english_option():
    return typer.Option(False, "--english", "-e", help="Translate to spoken text to English")

def help_option():
    return typer.Option(False, "--help", "-h", is_eager=True)

def file_option():
    return typer.Option(None, "--file", "-f", help="Path to audio/video file (default: record from microphone)")

def list_prompts_option():
    return typer.Option(False, "--list", "-l", help="List stored prompts")

def query_prompt_option():
    return typer.Option(False, "--query", "-q", help="Get and remove oldest stored prompt (queue behavior)")

def remove_prompt_option():
    return typer.Option(None, "--remove", "-r", help="Remove prompt by number (use with --list)")

def file_path_argument():
    return typer.Argument("/tmp/aitranscribe_record.mp3", help="Path to audio or video file")

# Logic Helper Functions
def get_post_process_prompt(english: bool, post_process: bool) -> str | None:
    if english:
        return PRE_PROCESS_MODES["english"]["prompt"]
    if post_process:
        return PRE_PROCESS_MODES["cleanup"]["prompt"]
    return None


def get_pre_process_prompt(mode: str) -> str | None:
    return PRE_PROCESS_MODES.get(mode, PRE_PROCESS_MODES["raw"])["prompt"]


def get_next_recording_version(temp_dir: str) -> int:
    base_name = "aitranscribe_record"
    pattern = re.compile(rf"^{re.escape(base_name)}_v(\d+)(?:\.prompted)?\.[a-zA-Z0-9]+$")
    max_v = 0
    try:
        for fname in os.listdir(temp_dir):
            match = pattern.match(fname)
            if match:
                version = int(match.group(1))
                if version > max_v:
                    max_v = version
    except OSError:
        pass
    return max_v + 1


def get_recording_file_paths(extension: str = ".mp3") -> tuple[str, str]:
    temp_dir = tempfile.gettempdir()
    next_version = get_next_recording_version(temp_dir)
    raw_wav_file = os.path.join(temp_dir, ".aitranscribe_raw.wav")
    final_audio_file = os.path.join(temp_dir, f"aitranscribe_record_v{next_version:03d}{extension}")
    return raw_wav_file, final_audio_file

def validate_api_keys(post_process: str | None) -> None:
    if not stt_client:
        console.print(f"Error: GROQ_API_KEY is not set or invalid in {CONFIG_FILE}.")
        raise typer.Exit(code=1)

    if post_process and not llm_client:
        provider_key = LLM_PROVIDERS.get(LLM_PROVIDER, LLM_PROVIDERS["openrouter"])["env_key"]
        console.print(f"Error: {provider_key} is not set but needed for post-processing. Set LLM_PROVIDER and the corresponding API key in {CONFIG_FILE}.")
        raise typer.Exit(code=1)

def wrap_text(text: str, max_length: int = 80) -> str:
    """Wrap text to specified max length, breaking at whitespace."""
    if len(text) <= max_length:
        return text

    words = text.split()
    wrapped_lines = []
    current_line = ""

    for word in words:
        if len(current_line + " " + word) <= max_length:
            if current_line:
                current_line += " " + word
            else:
                current_line = word
        else:
            wrapped_lines.append(current_line.strip())
            current_line = word

    if current_line.strip():
        wrapped_lines.append(current_line.strip())

    return "\n".join(wrapped_lines)

# Prompt Manager Class
class PromptManager:
    """Manages stored prompts in a SQLite database."""

    def __init__(self, prompts_file: Path):
        self.prompts_file = prompts_file
        self.prompts_file.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.prompts_file)
        # Explicitly use DELETE journal mode for cloud sync compatibility (OneDrive, Dropbox, etc.)
        # WAL mode creates extra -wal/-shm files that cause sync conflicts
        conn.execute("PRAGMA journal_mode=DELETE")
        return conn

    def _initialize_db(self) -> None:
        try:
            with self._connect() as conn:
                columns = conn.execute("PRAGMA table_info(prompts)").fetchall()
                if not columns:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS prompts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            prompt TEXT NOT NULL,
                            filename TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            summary TEXT DEFAULT NULL
                        )
                        """
                    )
                elif any(column[1] == "played_count" for column in columns):
                    conn.execute("ALTER TABLE prompts RENAME TO prompts_legacy")
                    conn.execute(
                        """
                        CREATE TABLE prompts (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            prompt TEXT NOT NULL,
                            filename TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            summary TEXT DEFAULT NULL
                        )
                        """
                    )
                    conn.execute(
                        """
                        INSERT INTO prompts (id, prompt, filename, created_at, summary)
                        SELECT id, prompt, filename, created_at, NULL
                        FROM prompts_legacy
                        ORDER BY id ASC
                        """
                    )
                    conn.execute("DROP TABLE prompts_legacy")
                elif not any(column[1] == "summary" for column in columns):
                    conn.execute("ALTER TABLE prompts ADD COLUMN summary TEXT DEFAULT NULL")
        except Exception as e:
            console.print(f"Warning: Could not initialize prompts database: {e}")

    @property
    def prompts(self) -> list[dict[str, Any]]:
        """Compatibility view of stored prompts for tests and callers."""
        return self._get_prompts(order="ASC")

    def _get_prompts(self, *, order: str = "ASC", limit: int | None = None) -> list[dict[str, Any]]:
        query = """
            SELECT id, prompt, filename, created_at, summary
            FROM prompts
            ORDER BY created_at {order}, id {order}
        """.format(order=order)
        params: tuple[Any, ...] = ()
        if limit is not None:
            query += " LIMIT ?"
            params = (limit,)

        try:
            with self._connect() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "prompt": row[1],
                        "filename": row[2],
                        "timestamp": row[3],
                        "summary": row[4],
                    }
                    for row in rows
                ]
        except Exception as e:
            console.print(f"Warning: Could not query prompts database: {e}")
            return []

    def recent_prompts(self, limit: int | None = None) -> list[dict[str, Any]]:
        return self._get_prompts(order="DESC", limit=limit)

    def count_prompts(self) -> int:
        try:
            with self._connect() as conn:
                row = conn.execute("SELECT COUNT(*) FROM prompts").fetchone()
                return int(row[0]) if row else 0
        except Exception as e:
            console.print(f"Warning: Could not count prompts: {e}")
            return 0

    def add_prompt(self, prompt: str, filename: str, summary: str | None = None) -> int | None:
        """Add a new prompt to the queue."""
        created_at = datetime.datetime.now().isoformat()
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO prompts (prompt, filename, created_at, summary)
                    VALUES (?, ?, ?, ?)
                    """,
                    (prompt, filename, created_at, summary),
                )
                lastrowid = cursor.lastrowid
                return int(lastrowid) if lastrowid is not None else None
        except Exception as e:
            console.print(f"Warning: Could not store prompt: {e}")
            return None

    def update_prompt(self, prompt_id: int, prompt: str) -> bool:
        """Update a stored prompt by database id."""
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE prompts SET prompt = ? WHERE id = ?",
                    (prompt, prompt_id),
                )
                return cursor.rowcount > 0
        except Exception as e:
            console.print(f"Warning: Could not update prompt: {e}")
            return False

    def update_prompt_summary(self, prompt_id: int, summary: str) -> bool:
        """Update a stored prompt summary by database id."""
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    "UPDATE prompts SET summary = ? WHERE id = ?",
                    (summary, prompt_id),
                )
                return cursor.rowcount > 0
        except Exception as e:
            console.print(f"Warning: Could not update prompt summary: {e}")
            return False

    def prompts_missing_summary(self) -> list[dict[str, Any]]:
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    """
                    SELECT id, prompt, filename, created_at, summary
                    FROM prompts
                    WHERE summary IS NULL OR TRIM(summary) = ''
                    ORDER BY created_at DESC, id DESC
                    """
                ).fetchall()
                return [
                    {
                        "id": row[0],
                        "prompt": row[1],
                        "filename": row[2],
                        "timestamp": row[3],
                        "summary": row[4],
                    }
                    for row in rows
                ]
        except Exception as e:
            console.print(f"Warning: Could not query prompts missing summary: {e}")
            return []

    def remove_prompt_by_id(self, prompt_id: int) -> bool:
        """Remove a stored prompt by database id."""
        try:
            with self._connect() as conn:
                cursor = conn.execute("DELETE FROM prompts WHERE id = ?", (prompt_id,))
                return cursor.rowcount > 0
        except Exception as e:
            console.print(f"Warning: Could not remove prompt: {e}")
            return False

    def list_prompts(self) -> None:
        """List all stored prompts in queue order."""
        stored_prompts = self.prompts
        if not stored_prompts:
            console.print("No prompts stored yet.")
            return

        console.print("Stored Prompts:")
        for i, prompt in enumerate(stored_prompts, 1):
            console.print(f"\n{i}. {prompt['prompt']}")
            console.print(f"    File: {prompt['filename']}")
            console.print(f"    Time: {prompt['timestamp']}")

    def query_prompt(self) -> str | None:
        """Get and remove the oldest stored prompt."""
        try:
            with self._connect() as conn:
                cursor = conn.execute(
                    """
                    SELECT id, prompt
                    FROM prompts
                    ORDER BY id ASC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()
                if not row:
                    console.print("No prompts in queue.")
                    return None

                conn.execute("DELETE FROM prompts WHERE id = ?", (row[0],))
                return row[1]
        except Exception as e:
            console.print(f"Warning: Could not query prompt: {e}")
            return None

    def remove_prompt(self, index: int) -> bool:
        """Remove a stored prompt by its 1-based --list index."""
        stored_prompts = self.prompts
        if not stored_prompts:
            console.print("No prompts to remove.")
            return False

        if index < 1 or index > len(stored_prompts):
            console.print(f"Error: Invalid index {index}. Valid range is 1-{len(stored_prompts)}.")
            return False

        removed_prompt = stored_prompts[index - 1]
        try:
            removed = self.remove_prompt_by_id(int(removed_prompt["id"]))
            if removed:
                console.print(f"Removed prompt {index}: {removed_prompt['prompt'][:50]}...")
                return True
            console.print(f"Warning: Could not remove prompt {index}.")
            return False
        except Exception as e:
            console.print(f"Warning: Could not remove prompt: {e}")
            return False


def generate_prompt_summary(text: str, llm_model: str) -> str | None:
    cleaned = text.strip()
    if not cleaned or not llm_client:
        return None

    summary = process_with_llm(llm_client, cleaned, SUMMARY_PROMPT, llm_model).strip()
    return summary or None


def backfill_missing_summaries(manager: PromptManager, llm_model: str) -> int:
    if not llm_client:
        return 0

    updated = 0
    for prompt in manager.prompts_missing_summary():
        summary = generate_prompt_summary(str(prompt.get("prompt", "")), llm_model)
        if not summary:
            continue
        if manager.update_prompt_summary(int(prompt["id"]), summary):
            updated += 1
    return updated

# Initialize PromptManager
prompt_manager = PromptManager(PROMPTS_FILE)


def process_recorded_audio_for_tui(
    audio_np: np.ndarray,
    settings: dict[str, Any],
    feedback_callback: Callable[[str, str], None] | None = None,
    transcript_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    prompt = get_pre_process_prompt(str(settings.get("pre_process_mode", "english")))
    verbose = bool(settings.get("verbose", False))

    if verbose:
        state["verbose"] = True

    validate_api_keys(prompt)

    raw_wav_file, final_mp3_file = get_recording_file_paths(".mp3")
    samplerate = 44100
    sf.write(raw_wav_file, audio_np, samplerate)

    def update_feedback(step_id: str, status: str) -> None:
        if feedback_callback:
            feedback_callback(step_id, status)

    try:
        update_feedback("compress", "active")
        compress_audio(raw_wav_file, output_path=final_mp3_file)
        update_feedback("compress", "done")
        if os.path.exists(raw_wav_file):
            os.remove(raw_wav_file)

        update_feedback("transcribe", "active")
        assert stt_client is not None
        transcript = transcribe_audio(stt_client, final_mp3_file, str(settings.get("stt_model", GROQ_STT_MODEL)))
        if transcript_callback:
            transcript_callback(transcript)
        update_feedback("transcribe", "done")

        final_text = transcript
        if prompt:
            update_feedback("post_process", "active")
            assert llm_client is not None
            final_text = process_with_llm(llm_client, transcript, prompt, str(settings.get("llm_model", LLM_MODEL)))
            update_feedback("post_process", "done")
        else:
            update_feedback("post_process", "done")

        append_mode = bool(settings.get("append_mode", False))
        if append_mode:
            prompt_id = None
        else:
            prompt_id = prompt_manager.add_prompt(final_text, final_mp3_file)

        return {
            "text": final_text,
            "raw_text": transcript,
            "file_path": final_mp3_file,
            "prompt_id": str(prompt_id) if prompt_id is not None else "",
        }
    finally:
        if os.path.exists(raw_wav_file):
            os.remove(raw_wav_file)


def process_file_for_tui(
    file_path: str,
    settings: dict[str, Any],
    feedback_callback: Callable[[str, str], None] | None = None,
    transcript_callback: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    prompt = get_pre_process_prompt(str(settings.get("pre_process_mode", "english")))
    verbose = bool(settings.get("verbose", False))

    if verbose:
        state["verbose"] = True

    validate_api_keys(prompt)

    source_file = file_path.strip()
    if not source_file:
        raise ValueError("Enter an audio file path first.")
    if not os.path.exists(source_file):
        raise FileNotFoundError(f"File not found: {source_file}")

    temp_dir = tempfile.gettempdir()
    next_v = get_next_recording_version(temp_dir)
    extension = os.path.splitext(source_file)[1] or ".mp3"
    working_file = os.path.join(temp_dir, f"aitranscribe_record_v{next_v:03d}{extension}")

    try:
        shutil.copy2(source_file, working_file)
        file_for_processing = working_file
    except Exception:
        file_for_processing = source_file

    def update_feedback(step_id: str, status: str) -> None:
        if feedback_callback:
            feedback_callback(step_id, status)

    try:
        update_feedback("compress", "done")
        update_feedback("transcribe", "active")
        chunks = chunk_audio(file_for_processing)
        transcripts = []
        for chunk_path in chunks:
            assert stt_client is not None
            transcripts.append(transcribe_audio(stt_client, chunk_path, str(settings.get("stt_model", GROQ_STT_MODEL))))
            if chunk_path != file_for_processing:
                os.remove(chunk_path)
        raw_text = " ".join(text for text in transcripts if text).strip()
        if transcript_callback:
            transcript_callback(raw_text)
        update_feedback("transcribe", "done")

        final_text = raw_text
        if prompt:
            update_feedback("post_process", "active")
            assert llm_client is not None
            final_text = process_with_llm(llm_client, final_text, prompt, str(settings.get("llm_model", LLM_MODEL)))
            update_feedback("post_process", "done")
        else:
            update_feedback("post_process", "done")

        append_mode = bool(settings.get("append_mode", False))
        if append_mode:
            prompt_id = None
        else:
            prompt_id = prompt_manager.add_prompt(final_text, file_for_processing)
        return {
            "text": final_text or "No transcript returned.",
            "raw_text": raw_text,
            "file_path": file_for_processing,
            "prompt_id": str(prompt_id) if prompt_id is not None else "",
        }
    except Exception:
        if file_for_processing == working_file and os.path.exists(working_file):
            pass
        raise


def launch_tui() -> None:
    from tui import AitranscribeTUI

    settings = get_tui_settings()
    app = AitranscribeTUI(
        prompt_manager=prompt_manager,
        process_audio=process_recorded_audio_for_tui,
        process_file=process_file_for_tui,
        stt_provider_name="Groq",
        llm_provider_name=LLM_PROVIDER,
        default_stt_model=settings["stt_model"],
        default_llm_model=settings["llm_model"],
        initial_settings=settings,
        persist_setting=persist_tui_setting,
        generate_summary=generate_prompt_summary,
        backfill_summaries=lambda: backfill_missing_summaries(prompt_manager, settings["llm_model"]),
    )
    app.run()

# Typer App
app = typer.Typer(
    help="aitranscribe: TUI-first terminal app for STT and LLM post-processing via multiple providers.",
    context_settings={"help_option_names": ["-h", "--help"]},
    add_completion=False,
    rich_markup_mode=None,
    no_args_is_help=False,
)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    file: str | None = file_option(),
    list_prompts: bool = list_prompts_option(),
    query_prompt: bool = query_prompt_option(),
    remove_prompt: int | None = remove_prompt_option(),
    english: bool = english_option(),
    llm_model: str = llm_model_option(),
    post_process: bool = post_process_option(),
    stt_model: str = stt_model_option(),
    verbose: bool = verbose_option(),
    help: bool = help_option(),
):
    """
    aitranscribe: TUI-first terminal app for STT and LLM post-processing.
    """
    if help:
        typer.echo(ctx.get_help())
        typer.echo()
        raise typer.Exit()

    if ctx.resilient_parsing:
        return

    state["verbose"] = verbose

    legacy_mode_requested = any(
        [
            file is not None,
            list_prompts,
            query_prompt,
            remove_prompt is not None,
            english,
            post_process,
            verbose,
            stt_model != GROQ_STT_MODEL,
            llm_model != LLM_MODEL,
        ]
    )

    if not legacy_mode_requested:
        launch_tui()
        raise typer.Exit(code=0)

    # Enforce mutual exclusivity between --english and --post-process
    if english and post_process:
        console.print("Error: Options --english and --post-process are mutually exclusive.")
        raise typer.Exit(code=1)

    # Handle prompt management commands
    if list_prompts:
        prompt_manager.list_prompts()
        raise typer.Exit(code=0)

    if remove_prompt is not None:
        prompt_manager.remove_prompt(remove_prompt)
        raise typer.Exit(code=0)

    if query_prompt:
        retrieved_prompt = prompt_manager.query_prompt()
        if retrieved_prompt:
            console.print(wrap_text(retrieved_prompt))
        raise typer.Exit(code=0)

    if file:
        transcribe_file(file, stt_model, llm_model, post_process, verbose, english)
    else:
        record_from_microphone(stt_model, llm_model, post_process, verbose, english)

def transcribe_file(file_path: str, stt_model: str, llm_model: str, post_process: bool, verbose: bool, english: bool):
    """Transcribe a local audio or video file using Groq STT and optionally process with LLM."""
    if verbose:
        state["verbose"] = True

    prompt = get_post_process_prompt(english, post_process)

    validate_api_keys(prompt)

    console.print(f"Preparing to transcribe file: {file_path}")
    console.print(f"STT Provider: Groq")
    console.print(f"STT Model: {stt_model}")
    if prompt:
        console.print(f"LLM Provider: {LLM_PROVIDER}")
        console.print(f"LLM Model: {llm_model}")

    if not os.path.exists(file_path):
        console.print(f"Error: File not found: {file_path}")
        raise typer.Exit(code=1)

    temp_dir = tempfile.gettempdir()
    next_v = get_next_recording_version(temp_dir)

    ext = os.path.splitext(file_path)[1]
    if not ext:
        ext = ".mp3"

    temp_file_path = os.path.join(temp_dir, f"aitranscribe_record_v{next_v:03d}{ext}")
    try:
        shutil.copy2(file_path, temp_file_path)
        file_path = temp_file_path
        console.print(f"Copied file to temp location: {file_path}")
    except Exception as e:
        console.print(f"Warning: Could not copy file to temp directory: {e}")

    try:
        with Progress(
            TextColumn("{task.description}"),
            transient=True,
            console=console
        ) as progress:
            # 1. Chunking
            progress.add_task(description="Checking file size and chunking...", total=None)
            chunks = chunk_audio(file_path)

            # 2. Transcribing
            full_transcript = []
            for i, chunk_path in enumerate(chunks):
                progress.update(progress.task_ids[0], description=f"Transcribing chunk {i+1}/{len(chunks)}...")
                assert stt_client is not None
                transcript = transcribe_audio(stt_client, chunk_path, stt_model)
                full_transcript.append(transcript)

                # Cleanup chunks if they were created
                if chunk_path != file_path:
                    os.remove(chunk_path)

            final_text = " ".join(t for t in full_transcript if t).strip()

        console.print("\nTranscription Complete:")
        console.print(wrap_text(final_text))

        # 3. Post-Processing
        if prompt:
            console.print(f"\nPrompt: {prompt}")

            with Progress(
                TextColumn("{task.description}"),
                transient=True,
                console=console
            ) as progress:
                progress.add_task(description="Processing with LLM...", total=None)
                assert llm_client is not None
                llm_result = process_with_llm(llm_client, final_text, prompt, llm_model)

            console.print("\nLLM Result:")
            console.print(wrap_text(llm_result))

            # Store LLM result in prompt queue
            prompt_manager.add_prompt(llm_result, file_path)
        else:
            # Store raw transcription in prompt queue
            prompt_manager.add_prompt(final_text, file_path)

    except Exception as e:
        console.print(f"An error occurred: {str(e)}")
        if state["verbose"]:
            console.print_exception()
        raise typer.Exit(code=1)

def record_from_microphone(stt_model: str, llm_model: str, post_process: bool, verbose: bool, english: bool):
    """Record audio from microphone in toggle mode and transcribe it using Groq."""
    if verbose:
        state["verbose"] = True

    prompt = get_post_process_prompt(english, post_process)

    validate_api_keys(prompt)

    samplerate = 44100
    channels = 1
    audio_data = []

    console.print("Toggle Recording")
    console.print(f"STT Provider: Groq")
    console.print(f"STT Model: {stt_model}")
    if prompt:
        console.print(f"LLM Provider: {LLM_PROVIDER}")
        console.print(f"LLM Model: {llm_model}")

    console.print("Press SPACE to start recording. Press SPACE again to stop. Press ESC to cancel.")

    recording_state = {
        "is_recording": False,
        "stop_event": False,
        "cancelled": False
    }

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> Any:
        if key == keyboard.Key.space:
            recording_state["is_recording"] = not recording_state["is_recording"]
            if not recording_state["is_recording"]:
                recording_state["stop_event"] = True
                return False
        elif key == keyboard.Key.esc:
            recording_state["stop_event"] = True
            recording_state["cancelled"] = True
            return False
        return None

    def on_release(key: keyboard.Key | keyboard.KeyCode | None) -> Any:
        return None

    listener = None
    try:
        listener = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True)
        listener.start()
    except Exception as e:
        if verbose:
            console.print(f"Warning: Could not start pynput listener: {e}")
        console.print("Falling back to terminal toggle-mode recording.")
        listener = None

    fd = None
    old_settings = None

    if os.name != 'nt':
        try:
            import termios
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            new_settings = termios.tcgetattr(fd)
            new_settings[3] = new_settings[3] & ~termios.ECHO
            new_settings[3] = new_settings[3] & ~termios.ICANON
            new_settings[6][termios.VMIN] = 0
            new_settings[6][termios.VTIME] = 0
            termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
        except (ImportError, Exception):
            pass

    if listener is None:
        if os.name == 'nt' or fd is not None:
            console.print("Press SPACE to start, SPACE again to stop. Press ESC to cancel.")
        else:
            console.print(f"Error: Could not set up keyboard input.")
            raise typer.Exit(code=1)

    try:
        # Hide cursor during recording
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()

        def callback(indata, frames, cb_time, status):
            if recording_state["is_recording"]:
                audio_data.append(indata.copy())

        with sd.InputStream(samplerate=samplerate, channels=channels, callback=callback):
            start_time = None
            last_update = 0.0
            total_start_time = time.time()
            timeout = 300 # 5 minutes total session timeout as safety

            while not recording_state["stop_event"]:
                if time.time() - total_start_time > timeout:
                    console.print("\nRecording session timed out.")
                    recording_state["stop_event"] = True
                    break

                # Check for fallback keyboard input
                if listener is None:
                    key = None
                    if os.name == 'nt':
                        import msvcrt
                        if msvcrt.kbhit():
                            char = msvcrt.getch()
                            # Handle ESC (27) or Space (32)
                            if char == b' ':
                                key = ' '
                            elif char == b'\x1b':
                                key = '\x1b'
                    else:
                        import select
                        if fd is not None and select.select([fd], [], [], 0.01)[0]:
                            key = sys.stdin.read(1)

                    if key == ' ':
                        if not recording_state["is_recording"]:
                            recording_state["is_recording"] = True
                        else:
                            recording_state["is_recording"] = False
                            recording_state["stop_event"] = True
                    elif key == '\x1b' or key == '\x03':
                        recording_state["stop_event"] = True
                        recording_state["cancelled"] = True
                        break

                if recording_state["is_recording"]:
                    now = time.time()
                    if start_time is None:
                        start_time = now
                        last_update = start_time
                        sys.stdout.write("\r\033[K⏺ Recording... 0s")
                        sys.stdout.flush()

                    if now - last_update >= 1.0:
                        duration = now - start_time
                        sys.stdout.write(f"\r\033[K⏺ Recording... {int(duration)}s")
                        sys.stdout.flush()
                        last_update = now
                else:
                    if start_time is not None:
                        # Transition from recording to stopped
                        sys.stdout.write("\n⏹ Recording stopped.\n")
                        sys.stdout.flush()
                        start_time = None

                time.sleep(0.05)

            if recording_state["cancelled"]:
                if recording_state["is_recording"]:
                    console.print("\nRecording cancelled.")
                return

    finally:
        # Show cursor again
        sys.stdout.write("\033[?25h")
        sys.stdout.flush()
        if listener is not None and listener.is_alive():
            listener.stop()
        # Restore terminal settings
        if os.name != 'nt':
            if fd is not None and old_settings is not None:
                try:
                    import termios
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                    termios.tcflush(fd, termios.TCIFLUSH)
                except Exception:
                    pass
        else:
            # Windows: Flush input buffer
            try:
                import msvcrt
                while msvcrt.kbhit():
                    msvcrt.getch()
            except Exception:
                pass

    if not audio_data:
        console.print("No audio recorded. Exiting.")
        return

    # Convert to numpy array
    audio_np = np.concatenate(audio_data, axis=0)

    raw_wav_file, final_mp3_file = get_recording_file_paths(".mp3")

    sf.write(raw_wav_file, audio_np, samplerate)

    try:
        with Progress(
            TextColumn("{task.description}"),
            transient=True,
            console=console
        ) as progress:
            # First, compress WAV to MP3 to save bandwidth and potentially tokens
            progress.add_task(description="Compressing audio...", total=None)
            compress_audio(raw_wav_file, output_path=final_mp3_file)

            # Clean up the raw wav now that we have the mp3
            if os.path.exists(raw_wav_file):
                os.remove(raw_wav_file)

            console.print(f"Audio saved to {final_mp3_file}")

            progress.add_task(description="Transcribing audio...", total=None)
            assert stt_client is not None
            transcript = transcribe_audio(stt_client, final_mp3_file, stt_model)

        console.print("\nTranscription Complete:")
        console.print(wrap_text(transcript))

        # Post-Processing
        if prompt:
            console.print(f"\nPrompt: {prompt}")

            with Progress(
                TextColumn("{task.description}"),
                transient=True,
                console=console
            ) as progress:
                progress.add_task(description="Processing with LLM...", total=None)
                assert llm_client is not None
                llm_result = process_with_llm(llm_client, transcript, prompt, llm_model)

            console.print("\nLLM Result:")
            console.print(wrap_text(llm_result))

            # Store LLM result in prompt queue
            prompt_manager.add_prompt(llm_result, final_mp3_file)
        else:
            # Store raw transcription in prompt queue
            prompt_manager.add_prompt(transcript, final_mp3_file)

    except Exception as e:
        console.print(f"An error occurred: {str(e)}")
        if state["verbose"]:
            console.print_exception()
        # Keep the file on disk if there is an error
        console.print(f"Retaining recorded file for debugging: {final_mp3_file}")
    else:
        # We now keep the final mp3 file on disk for reuse, as requested
        # We only clean up the raw uncompressed wav file
        if os.path.exists(raw_wav_file):
            os.remove(raw_wav_file)

if __name__ == "__main__":
    app()
