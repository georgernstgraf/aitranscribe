# aitranscribe

A powerful CLI tool and Android app for audio transcription and LLM post-processing, powered by **GROQ** for lightning-fast STT and **OpenRouter** for LLM post-processing.

## 🚀 Features

* **🎙️ Microphone Recording:** Capture audio directly from your terminal using a push-to-talk mechanism (Hold SPACE to record).
* **📁 File Transcription:** Process local audio and video files (`.mp3`, `.wav`, `.mp4`, `.m4a`, etc.) using Groq's whisper models.
* **✂️ Auto-Chunking:** Automatically splits large audio files to bypass standard API file size limits (GROQ currently limits audio files to 25MB).
* **✨ LLM Post-Processing:** Refine your transcriptions using OpenRouter LLMs for grammar correction, summarization, or translation.
* **📜 Prompt Management:** Local queue to store and retrieve transcription history for easy access and processing.

## 🛠️ Technology Stack

### CLI (Python)
* **Language:** Python 3.12+
* **CLI Framework:** [Typer](https://typer.tiangolo.com/) for a modern, clean command-line interface.
* **UI/Output:** [Rich](https://rich.readthedocs.io/) for beautiful console output, progress bars, and Markdown rendering.
* **Audio Processing:** [pydub](https://github.com/jiaaro/pydub) for handling various audio formats and chunking large files.
* **Microphone Capture:** `sounddevice`, `soundfile`, and `pynput` for cross-platform push-to-talk recording (supports Windows via `msvcrt` fallback).

### Android App (Kotlin)
* **Language:** Kotlin
* **UI:** Jetpack Compose (Material 3)
* **Database:** Room (SQLite)
* **Dependency Injection:** Hilt
* **Networking:** Retrofit + OkHttp
* **Background Processing:** WorkManager
* **Distribution:** F-Droid (FOSS)

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Python 3.12** or higher.
2. **FFmpeg:** Required by `pydub` to manipulate non-WAV audio formats (like MP3 or MP4).
    * **macOS:** `brew install ffmpeg`
    * **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`
    * **Windows:** `winget install ffmpeg` or download from [ffmpeg.org](https://ffmpeg.org/download.html).

## 💻 Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/aitranscribe.git
    cd aitranscribe
    ```

2. Create and activate a virtual environment:

    ```bash
    python -m venv venv
    # Linux/macOS:
    source venv/bin/activate
    # Windows:
    venv\Scripts\activate
    ```

3. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Make the tool globally accessible:

    **Linux/macOS:**
    ```bash
    chmod +x aitranscribe
    sudo ln -s "$(pwd)/aitranscribe" /usr/local/bin/aitranscribe
    ```

    **Windows:**
    Add the repository directory to your system's **PATH** environment variable. The `aitranscribe.bat` wrapper will handle execution.

## ⚙️ Configuration

`aitranscribe` uses a global configuration file:
* **Linux/macOS:** `~/.config/aitranscribe/config`
* **Windows:** `%APPDATA%\aitranscribe\config`

On the first run, the tool will automatically create a template for you.


1. Open the file using your favorite editor:

   ```bash
   nano ~/.config/aitranscribe/config
   ```

2. Add your API keys and preferred models:

   ```env
   GROQ_API_KEY="your_groq_api_key_here"
   OPENROUTER_API_KEY="your_openrouter_api_key_here"
   GROQ_STT_MODEL="whisper-large-v3-turbo"
   OPENROUTER_LLM_MODEL="anthropic/claude-3-haiku"
   ```

## 🎯 Usage Examples

Since `aitranscribe` is symlinked to your global path, you can run it from any directory!

**Record from microphone (Default Mode, Push-to-Talk):**
Hold **SPACE** to record, release to stop. Press **ESC** to cancel.
```bash
aitranscribe
```

**Transcribe a local file:**
```bash
aitranscribe --file path/to/audio.mp3
```

**Translate to English directly:**
```bash
aitranscribe --file audio_in_other_language.mp3 --english
```

**Apply LLM Post-Processing:**
Correct grammar and structure the text automatically:
```bash
aitranscribe --post-process
```
Or provide a custom prompt for processing:
```bash
aitranscribe --file meeting.wav --post-process "Summarize this meeting into bullet points"
```

**Manage Prompt History:**
```bash
aitranscribe --list      # Show all stored transcriptions
aitranscribe --query     # Retrieve the oldest transcription from the queue
aitranscribe --remove 1  # Remove a specific transcription by its ID
```

**Start fresh (Clean up temp files):**
```bash
aitranscribe --new
```

## 🧪 Testing

We provide a test infrastructure to ensure dependencies are installed and CLI works.

1. Install test dependencies:

   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run tests:

   ```bash
   pytest
   ```

## 🏗️ Code Architecture

The project follows clean code principles with focus on maintainability and testability:

* **Option Factory Pattern:** CLI options are defined through factory functions for consistency and reusability.
* **Shared Logic Helpers:** Common operations are extracted into reusable utility functions.
* **Comprehensive Testing:** Unit and integration tests cover core logic and CLI interactions.
* **Single Source of Truth:** CLI parameters and configuration are centralized.

## 📱 Android App

An Android version of AITranscribe is also available in the `android/` subdirectory. See [android/README.md](android/README.md) for details.

**Features:**
- Push-to-talk recording
- GROQ STT + OpenRouter LLM processing
- SQLite storage with view status tracking
- Search with date range and text filters
- Offline queue support
- Background transcription
- Dark/Light theme support

**Building:**
```bash
cd android
./gradlew assembleDebug
```

## 📄 License

MIT License
