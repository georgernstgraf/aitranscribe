# aitranscribe

A TUI-first terminal app and Android app for audio transcription and LLM post-processing, powered by **GROQ** for lightning-fast STT and multiple LLM providers for post-processing.

## 🚀 Features

* **🖥️ Rich TUI:** Starts in a framed terminal UI with dedicated status, transcript, feedback log, and configuration panels.
* **🎙️ Toggle Recording:** Start recording with **SPACE** and finish with **SPACE** again, regardless of Wayland or X11.
* **📁 File Transcription:** Process local audio and video files (`.mp3`, `.wav`, `.mp4`, `.m4a`, etc.) using Groq's whisper models.
* **✂️ Auto-Chunking:** Automatically splits large audio files to bypass standard API file size limits (GROQ currently limits audio files to 25MB).
* **✨ LLM Post-Processing:** Refine your transcriptions using LLMs for grammar correction, summarization, or translation. Supports OpenRouter, Cohere, and z.ai.
* **📜 Prompt Management:** Local queue to store transcription history, review unread items, and mark all transcriptions as read from the TUI.

## 🛠️ Technology Stack

### CLI (Python)
* **Language:** Python 3.12+
* **CLI Framework:** [Typer](https://typer.tiangolo.com/) for a modern, clean command-line interface.
* **UI/Output:** [Rich](https://rich.readthedocs.io/) and [Textual](https://textual.textualize.io/) for the terminal interface, panels, and keyboard/mouse interactions.
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

   **Example 1: OpenRouter (default)**
   ```env
   # Speech-to-Text Configuration
   GROQ_API_KEY="your_groq_api_key_here"
   GROQ_STT_MODEL="whisper-large-v3-turbo"

   # LLM Post-Processing Configuration
   LLM_PROVIDER="openrouter"
   OPENROUTER_API_KEY="your_openrouter_api_key_here"
   OPENROUTER_LLM_MODEL="anthropic/claude-3-haiku"
   ```

   **Example 2: Cohere with GLM-5**
   ```env
   # Speech-to-Text Configuration
   GROQ_API_KEY="your_groq_api_key_here"
   GROQ_STT_MODEL="whisper-large-v3-turbo"

   # LLM Post-Processing Configuration
   LLM_PROVIDER="cohere"
   COHERE_API_KEY="your_cohere_api_key_here"
   COHERE_LLM_MODEL="glm-5"
   ```

   **Example 3: z.ai**
   ```env
   # Speech-to-Text Configuration
   GROQ_API_KEY="your_groq_api_key_here"
   GROQ_STT_MODEL="whisper-large-v3-turbo"

   # LLM Post-Processing Configuration
   LLM_PROVIDER="z.ai"
   ZAI_API_KEY="your_zai_api_key_here"
   ZAI_LLM_MODEL="glm-5"
   ```

### Supported LLM Providers

| Provider | `LLM_PROVIDER` value | Default Model |
|----------|---------------------|---------------|
| OpenRouter | `openrouter` | `anthropic/claude-3-haiku` |
| Cohere | `cohere` | `command-r` |
| z.ai | `z.ai` | `glm-5` |

## 🎯 Usage Examples

Since `aitranscribe` is symlinked to your global path, you can run it from any directory!

**Launch the TUI (default mode):**
Press **SPACE** to start recording, **SPACE** again to finish, and **Q** to quit.
```bash
aitranscribe
```

Inside the TUI you can:
- switch the pre-processing mode between raw transcription, cleanup, and English translation
- inspect a four-line feedback log for STT and pre-processing progress
- configure models and extra settings in dedicated panels
- mark all unread transcriptions as read with the on-screen button

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
