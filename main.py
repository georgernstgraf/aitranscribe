import os
import typer
import sounddevice as sd
import soundfile as sf
import numpy as np
import tempfile
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from dotenv import load_dotenv
from pynput import keyboard
from openai import OpenAI
from core import chunk_audio, transcribe_audio, process_with_llm

app = typer.Typer(help="aitranscribe: CLI tool for STT and LLM post-processing via OpenRouter.")
console = Console()
state = {"verbose": False}

@app.callback()
def main_callback(verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose error outputs")):
    state["verbose"] = verbose

# Configuration Directory
CONFIG_DIR = Path.home() / ".config" / "aitranscribe"
CONFIG_FILE = CONFIG_DIR / "config"

# Create default config if it doesn't exist
if not CONFIG_FILE.exists():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        f.write('OPENROUTER_API_KEY="your_openrouter_api_key_here"\n')
        f.write('OPENROUTER_STT_MODEL="openai/whisper-large-v3"\n')
        f.write('OPENROUTER_LLM_MODEL="anthropic/claude-3-haiku"\n')
    console.print(f"[yellow]Created default configuration at {CONFIG_FILE}[/yellow]")
    console.print("[yellow]Please edit this file to add your OPENROUTER_API_KEY before running the tool.[/yellow]")

# Load environment variables from global config
load_dotenv(dotenv_path=CONFIG_FILE)

# OpenRouter client configuration
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_STT_MODEL = os.getenv("OPENROUTER_STT_MODEL", "openai/whisper-large-v3")
OPENROUTER_LLM_MODEL = os.getenv("OPENROUTER_LLM_MODEL", "anthropic/claude-3-haiku")

# Initialize OpenAI client pointing to OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
) if OPENROUTER_API_KEY and OPENROUTER_API_KEY != "your_openrouter_api_key_here" else None

@app.command()
def file(
    file_path: str = typer.Argument(..., help="Path to the audio or video file"),
    post_process: str = typer.Option(None, "--post-process", help="Prompt for LLM post-processing"),
    stt_model: str = typer.Option(OPENROUTER_STT_MODEL, help="OpenRouter STT model to use"),
    llm_model: str = typer.Option(OPENROUTER_LLM_MODEL, help="OpenRouter LLM model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose error outputs")
):
    """
    Transcribe a local audio or video file.
    """
    if verbose:
        state["verbose"] = True

    if not client:
        console.print(f"[red]Error: OPENROUTER_API_KEY is not set or invalid in {CONFIG_FILE}.[/red]")
        raise typer.Exit(code=1)
        
    console.print(f"[blue]Preparing to transcribe file: {file_path}[/blue]")
    console.print(f"STT Model: [cyan]{stt_model}[/cyan]")
    
    if not os.path.exists(file_path):
        console.print(f"[red]Error: File not found: {file_path}[/red]")
        raise typer.Exit(code=1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            # 1. Chunking
            progress.add_task(description="Checking file size and chunking...", total=None)
            chunks = chunk_audio(file_path)
            
            # 2. Transcribing
            full_transcript = []
            for i, chunk_path in enumerate(chunks):
                progress.update(progress.task_ids[0], description=f"Transcribing chunk {i+1}/{len(chunks)}...")
                transcript = transcribe_audio(client, chunk_path, stt_model)
                full_transcript.append(transcript)
                
                # Cleanup chunks if they were created
                if chunk_path != file_path:
                    os.remove(chunk_path)

            final_text = " ".join(full_transcript)
        
        console.print("\n[bold green]Transcription Complete:[/bold green]")
        console.print(final_text)

        # 3. Post-Processing
        if post_process:
            console.print(f"\n[bold blue]Applying LLM Post-Processing...[/bold blue]")
            console.print(f"Prompt: [magenta]{post_process}[/magenta]")
            console.print(f"Model: [cyan]{llm_model}[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Processing with LLM...", total=None)
                llm_result = process_with_llm(client, final_text, post_process, llm_model)
                
            console.print("\n[bold green]LLM Result:[/bold green]")
            console.print(llm_result)

    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
        if state["verbose"]:
            console.print_exception()
        raise typer.Exit(code=1)

@app.command()
def record(
    post_process: str = typer.Option(None, "--post-process", help="Prompt for LLM post-processing"),
    stt_model: str = typer.Option(OPENROUTER_STT_MODEL, help="OpenRouter STT model to use"),
    llm_model: str = typer.Option(OPENROUTER_LLM_MODEL, help="OpenRouter LLM model to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose error outputs")
):
    """
    Record audio from the microphone (Push-to-Talk) and transcribe it.
    Hold SPACEBAR to record.
    """
    if verbose:
        state["verbose"] = True

    if not client:
        console.print(f"[red]Error: OPENROUTER_API_KEY is not set or invalid in {CONFIG_FILE}.[/red]")
        raise typer.Exit(code=1)
        
    samplerate = 44100
    channels = 1
    audio_data = []
    
    is_recording = False
    stop_event = False

    def on_press(key):
        nonlocal is_recording, stop_event
        if key == keyboard.Key.space and not is_recording:
            is_recording = True
            console.print("[green]⏺ Recording... (Speak now)[/green]")
        elif key == keyboard.Key.esc:
            stop_event = True

    def on_release(key):
        nonlocal is_recording, stop_event
        if key == keyboard.Key.space and is_recording:
            is_recording = False
            stop_event = True
            console.print("[yellow]⏹ Recording stopped.[/yellow]")

    console.print("[bold]Push-to-Talk Recording[/bold]")
    console.print(f"STT Model: [cyan]{stt_model}[/cyan]")
    console.print("Press and hold [bold cyan]SPACEBAR[/bold cyan] to record. Release to transcribe. Press ESC to cancel.")

    # We use a listener for the spacebar
    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        def callback(indata, frames, time, status):
            if is_recording:
                audio_data.append(indata.copy())

        with sd.InputStream(samplerate=samplerate, channels=channels, callback=callback):
            while not stop_event:
                sd.sleep(100)
                
    if not audio_data:
        console.print("[red]No audio recorded. Exiting.[/red]")
        return

    # Convert to numpy array
    audio_np = np.concatenate(audio_data, axis=0)
    
    # Save to temp file
    temp_dir = tempfile.gettempdir()
    temp_file = os.path.join(temp_dir, "aitranscribe_record.wav")
    sf.write(temp_file, audio_np, samplerate)
    
    console.print(f"[blue]Audio saved temporarily to {temp_file}[/blue]")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Transcribing audio...", total=None)
            transcript = transcribe_audio(client, temp_file, stt_model)
        
        console.print("\n[bold green]Transcription Complete:[/bold green]")
        console.print(transcript)

        # Post-Processing
        if post_process:
            console.print(f"\n[bold blue]Applying LLM Post-Processing...[/bold blue]")
            console.print(f"Prompt: [magenta]{post_process}[/magenta]")
            console.print(f"Model: [cyan]{llm_model}[/cyan]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                progress.add_task(description="Processing with LLM...", total=None)
                llm_result = process_with_llm(client, transcript, post_process, llm_model)
                
            console.print("\n[bold green]LLM Result:[/bold green]")
            console.print(llm_result)

    except Exception as e:
        console.print(f"[red]An error occurred: {str(e)}[/red]")
        if state["verbose"]:
            console.print_exception()
        # Keep the file on disk if there is an error
        console.print(f"[yellow]Retaining recorded file for debugging: {temp_file}[/yellow]")
    else:
        # Cleanup temporary file only on success
        if os.path.exists(temp_file):
            os.remove(temp_file)

if __name__ == "__main__":
    app()