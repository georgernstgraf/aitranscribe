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
import glob
import json
import datetime
from pathlib import Path
from typing import Any
from rich.console import Console
from rich.progress import Progress, TextColumn
from dotenv import load_dotenv
from openai import OpenAI
from pynput import keyboard
from core import chunk_audio, transcribe_audio, process_with_llm, compress_audio

console = Console(highlight=False, color_system=None)
state = {"verbose": False}

# Configuration Directory
if os.name == 'nt':
    # Windows: %APPDATA%\aitranscribe
    appdata = os.getenv('APPDATA')
    if appdata:
        CONFIG_DIR = Path(appdata) / "aitranscribe"
    else:
        CONFIG_DIR = Path.home() / "AppData" / "Roaming" / "aitranscribe"
else:
    # Linux/macOS: ~/.config/aitranscribe
    CONFIG_DIR = Path.home() / ".config" / "aitranscribe"

CONFIG_FILE = CONFIG_DIR / "config"
PROMPTS_FILE = CONFIG_DIR / "prompts.json"

# Create default config if it doesn't exist
if not CONFIG_FILE.exists() or "GROQ_API_KEY" not in CONFIG_FILE.read_text():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    # If file exists but is missing Groq keys (migration), append them
    mode = "a" if CONFIG_FILE.exists() else "w"
    with open(CONFIG_FILE, mode) as f:
        if mode == "w":
            f.write('GROQ_API_KEY="your_groq_api_key_here"\n')
            f.write('OPENROUTER_API_KEY="your_openrouter_api_key_here"\n')
        else:
            f.write('\n# Added during Groq migration\n')
            f.write('GROQ_API_KEY="your_groq_api_key_here"\n')
        f.write('GROQ_STT_MODEL="whisper-large-v3-turbo"\n')
        if mode == "w":
            f.write('OPENROUTER_LLM_MODEL="anthropic/claude-3-haiku"\n')
        f.write(f'PROMPTS_FILE="{PROMPTS_FILE}"\n')
    console.print(f"Updated/Created configuration at {CONFIG_FILE}")
    console.print("Please edit this file to add your API keys before running the tool.")

# Load environment variables from global config
load_dotenv(dotenv_path=CONFIG_FILE)

PROMPTS_FILE = Path(os.getenv("PROMPTS_FILE", str(PROMPTS_FILE)))

# API Keys and Models
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GROQ_STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
OPENROUTER_LLM_MODEL = os.getenv("OPENROUTER_LLM_MODEL", "anthropic/claude-3-haiku")

# Initialize OpenAI client pointing to Groq for STT
stt_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
) if GROQ_API_KEY and GROQ_API_KEY != "your_groq_api_key_here" else None

# Initialize OpenAI client pointing to OpenRouter for LLM
llm_client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
) if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "your_openrouter_api_key_here" else None

# Option Factory Functions
def post_process_option():
    return typer.Option(False, "--post-process", "-p", help="Refine text: correct grammar, remove fillers, and structure clearly")

def stt_model_option():
    return typer.Option(GROQ_STT_MODEL, help="Groq STT model to use")

def llm_model_option():
    return typer.Option(OPENROUTER_LLM_MODEL, "--llm-model", "-m", help="OpenRouter LLM model to use")

def verbose_option():
    return typer.Option(False, "--verbose", "-v", help="Show verbose error outputs")

def new_option():
    return typer.Option(False, "--new", "-n", help="Start fresh: Delete all previous 'aitranscribe_record' files")

def english_option():
    return typer.Option(False, "--english", "-e", help="Translate to spoken text to English")

def help_option():
    return typer.Option(False, "--help", "-h", is_eager=True)

def file_option():
    return typer.Option(None, "--file", "-f", help="Path to audio/video file (default: record from microphone)")

def list_prompts_option():
    return typer.Option(False, "--list", "-l", help="List all stored prompts")

def query_prompt_option():
    return typer.Option(False, "--query", "-q", help="Get oldest prompt (queue behavior)")

def remove_prompt_option():
    return typer.Option(None, "--remove", "-r", help="Remove prompt by number (use with --list)")

def file_path_argument():
    return typer.Argument("/tmp/aitranscribe_record.mp3", help="Path to audio or video file")

# Logic Helper Functions
def get_post_process_prompt(english: bool, post_process: bool) -> str | None:
    if english:
        return "Please translate the following text to English, correct grammatical errors, remove filler words, and structure it clearly."
    if post_process:
        return "Please correct grammatical errors, remove filler words, and structure the following text."
    return None

def cleanup_old_records() -> int:
    temp_dir = tempfile.gettempdir()
    base_name = "aitranscribe_record"
    pattern = os.path.join(temp_dir, f"{base_name}_*")
    deleted_count = 0
    for f in glob.glob(pattern):
        try:
            os.remove(f)
            deleted_count += 1
        except OSError as e:
            console.print(f"Could not delete {f}: {e}")
    if deleted_count > 0:
        console.print(f"Deleted {deleted_count} previous recording(s) in {temp_dir}")
    return deleted_count

def validate_api_keys(post_process: str | None) -> None:
    if not stt_client:
        console.print(f"Error: GROQ_API_KEY is not set or invalid in {CONFIG_FILE}.")
        raise typer.Exit(code=1)

    if post_process and not llm_client:
        console.print(f"Error: OPENROUTER_API_KEY is not set but needed for post-processing.")
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
    """Manages stored prompts in a JSON file."""

    def __init__(self, prompts_file: Path):
        self.prompts_file = prompts_file
        self.prompts_file.parent.mkdir(parents=True, exist_ok=True)
        self.prompts = self._load_prompts()

    def _load_prompts(self) -> list:
        """Load prompts from JSON file."""
        if self.prompts_file.exists():
            try:
                with open(self.prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                console.print(f"Warning: Could not load prompts file: {e}")
                return []
        return []

    def _save_prompts(self) -> None:
        """Save prompts to JSON file."""
        try:
            with open(self.prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.prompts, f, indent=2)
        except Exception as e:
            console.print(f"Warning: Could not save prompts file: {e}")

    def add_prompt(self, prompt: str, filename: str) -> None:
        """Add a new prompt to the end of the list."""
        prompt_entry = {
            "prompt": wrap_text(prompt),
            "filename": filename,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.prompts.append(prompt_entry)
        self._save_prompts()

    def list_prompts(self) -> None:
        """List all stored prompts in order."""
        if not self.prompts:
            console.print("No prompts stored yet.")
            return

        console.print("Stored Prompts:")
        for i, prompt in enumerate(self.prompts, 1):
            console.print(f"\n{i}. {prompt['prompt']}")
            console.print(f"    File: {prompt['filename']}")
            console.print(f"    Time: {prompt['timestamp']}")

    def query_prompt(self) -> str | None:
        """Get the oldest prompt and remove it from the list (queue behavior)."""
        if not self.prompts:
            console.print("No prompts in queue.")
            return None

        oldest_prompt = self.prompts.pop(0)
        self._save_prompts()
        return oldest_prompt['prompt']

    def remove_prompt(self, index: int) -> bool:
        """Remove a prompt by its 1-based index."""
        if not self.prompts:
            console.print("No prompts to remove.")
            return False

        if index < 1 or index > len(self.prompts):
            console.print(f"Error: Invalid index {index}. Valid range is 1-{len(self.prompts)}.")
            return False

        removed_prompt = self.prompts.pop(index - 1)
        self._save_prompts()
        console.print(f"Removed prompt {index}: {removed_prompt['prompt'][:50]}...")
        return True

# Initialize PromptManager
prompt_manager = PromptManager(PROMPTS_FILE)

# Typer App
app = typer.Typer(
    help="aitranscribe: CLI tool for STT and LLM post-processing via OpenRouter.",
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
    new: bool = new_option(),
    post_process: bool = post_process_option(),
    stt_model: str = stt_model_option(),
    verbose: bool = verbose_option(),
    help: bool = help_option(),
):
    """
    aitranscribe: CLI tool for STT and LLM post-processing via OpenRouter.
    """
    if help:
        typer.echo(ctx.get_help())
        typer.echo()
        raise typer.Exit()

    if ctx.resilient_parsing:
        return

    state["verbose"] = verbose

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
            console.print(retrieved_prompt)
        raise typer.Exit(code=0)

    if file:
        transcribe_file(file, stt_model, llm_model, post_process, verbose, english, new)
    else:
        record_from_microphone(stt_model, llm_model, post_process, verbose, english, new)

def transcribe_file(file_path: str, stt_model: str, llm_model: str, post_process: bool, verbose: bool, english: bool, new: bool):
    """Transcribe a local audio or video file using Groq STT and optionally process with OpenRouter LLM."""
    if verbose:
        state["verbose"] = True

    prompt = get_post_process_prompt(english, post_process)

    if new:
        cleanup_old_records()

    validate_api_keys(prompt)

    console.print(f"Preparing to transcribe file: {file_path}")
    console.print(f"STT Model: {stt_model}")
    console.print(f"LLM Model: {llm_model}")

    if not os.path.exists(file_path):
        console.print(f"Error: File not found: {file_path}")
        raise typer.Exit(code=1)

    # Determine the next version number for output files in temp_dir
    temp_dir = tempfile.gettempdir()
    base_name = "aitranscribe_record"
    pattern = re.compile(rf"^{re.escape(base_name)}_v(\d+)(?:\.prompted)?\.[a-zA-Z0-9]+$")
    max_v = 0
    try:
        for fname in os.listdir(temp_dir):
            match = pattern.match(fname)
            if match:
                v = int(match.group(1))
                if v > max_v:
                    max_v = v
    except OSError:
        pass
    next_v = max_v + 1

    ext = os.path.splitext(file_path)[1]
    if not ext:
        ext = ".mp3"

    temp_file_path = os.path.join(temp_dir, f"{base_name}_v{next_v:02d}{ext}")
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
        console.print(final_text)

        # 3. Post-Processing
        if prompt:
            console.print(f"\nApplying LLM Post-Processing...")
            console.print(f"Prompt: {prompt}")
            console.print(f"Model: {llm_model}")

            with Progress(
                TextColumn("{task.description}"),
                transient=True,
                console=console
            ) as progress:
                progress.add_task(description="Processing with LLM...", total=None)
                assert llm_client is not None
                llm_result = process_with_llm(llm_client, final_text, prompt, llm_model)

            console.print("\nLLM Result:")
            console.print(llm_result)

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

def record_from_microphone(stt_model: str, llm_model: str, post_process: bool, verbose: bool, english: bool, new: bool):
    """Record audio from microphone (Push-to-Talk) and transcribe it using Groq."""
    if verbose:
        state["verbose"] = True

    prompt = get_post_process_prompt(english, post_process)

    if new:
        cleanup_old_records()

    validate_api_keys(prompt)

    samplerate = 44100
    channels = 1
    audio_data = []

    console.print("Push-to-Talk Recording")
    console.print(f"STT Model: {stt_model}")
    console.print(f"LLM Model: {llm_model}")
    console.print("Hold SPACE to record. Release to stop. Press ESC to cancel.")

    # Shared state for the listener
    recording_state = {
        "is_recording": False,
        "stop_event": False,
        "cancelled": False
    }

    def on_press(key: keyboard.Key | keyboard.KeyCode | None) -> Any:
        if key == keyboard.Key.space:
            if not recording_state["is_recording"]:
                recording_state["is_recording"] = True
                # UI is handled in the main loop
        elif key == keyboard.Key.esc:
            recording_state["stop_event"] = True
            recording_state["cancelled"] = True
            return False
        return None

    def on_release(key: keyboard.Key | keyboard.KeyCode | None) -> Any:
        if key == keyboard.Key.space:
            if recording_state["is_recording"]:
                recording_state["is_recording"] = False
                recording_state["stop_event"] = True
                return False
        return None

    listener = None
    try:
        listener = keyboard.Listener(on_press=on_press, on_release=on_release, suppress=True)  # type: ignore
        listener.start()
    except Exception as e:
        if verbose:
            console.print(f"Warning: Could not start pynput listener: {e}")
        console.print("Falling back to toggle-mode recording (press SPACE to start/stop).")
        # Fallback to termios/msvcrt handled below by checking if listener is None

    fd = None
    old_settings = None
    
    # Try to set up terminal to disable echo and canonical mode regardless of listener type
    # This prevents auto-repeat from flooding the terminal buffer
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
        # Check if we can at least use msvcrt (Windows) or termios (Unix)
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

    # Save to temp file
    temp_dir = tempfile.gettempdir()

    # Determine the next version number for output files
    base_name = "aitranscribe_record"
    pattern = re.compile(rf"^{re.escape(base_name)}_v(\d+)(?:\.prompted)?\.[a-zA-Z0-9]+$")
    max_v = 0
    try:
        for fname in os.listdir(temp_dir):
            match = pattern.match(fname)
            if match:
                v = int(match.group(1))
                if v > max_v:
                    max_v = v
    except OSError:
        pass
    next_v = max_v + 1

    raw_wav_file = os.path.join(temp_dir, ".aitranscribe_raw.wav")
    final_mp3_file = os.path.join(temp_dir, f"{base_name}_v{next_v:02d}.mp3")

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
        console.print(transcript)

        # Post-Processing
        if prompt:
            console.print(f"\nApplying LLM Post-Processing...")
            console.print(f"Prompt: {prompt}")
            console.print(f"Model: {llm_model}")

            with Progress(
                TextColumn("{task.description}"),
                transient=True,
                console=console
            ) as progress:
                progress.add_task(description="Processing with LLM...", total=None)
                assert llm_client is not None
                llm_result = process_with_llm(llm_client, transcript, prompt, llm_model)

            console.print("\nLLM Result:")
            console.print(llm_result)

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
