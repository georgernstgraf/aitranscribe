# aitranscribe

A powerful CLI tool for audio transcription and LLM post-processing, powered by **Groq** for lightning-fast STT and **OpenRouter** for LLM post-processing.

## 🚀 Features

* **📁 File Transcription:** Process local audio and video files (`.mp3`, `.wav`, `.mp4`, `.m4a`, etc.) using Groq's whisper models.
* **🎙️ Microphone Recording:** Capture audio directly from your terminal and transcribe it on the fly.
* **✂️ Auto-Chunking:** Automatically splits large audio files to bypass standard API file size limits (Groq currently limits audio files to 25MB).
* **✨ LLM Post-Processing:** Feed your transcriptions back into an OpenRouter LLM for summarization, formatting, or action-item extraction.

## 🛠️ Technology Stack

* **Language:** Python 3.12+
* **CLI Framework:** [Typer](https://typer.tiangolo.com/) for a modern, clean command-line interface.
* **UI/Output:** [Rich](https://rich.readthedocs.io/) for beautiful console output, progress bars, and Markdown rendering.
* **Audio Processing:** [pydub](https://github.com/jiaaro/pydub) for handling various audio formats and chunking large files.
* **Microphone Capture:** `sounddevice`, `soundfile`, and `pynput` for cross-platform push-to-talk recording.
* **API Client:** The official `openai` Python SDK (configured to route through OpenRouter).

## 📋 Prerequisites

Before you begin, ensure you have the following installed on your system:

1. **Python 3.12** or higher.
2. **FFmpeg:** Required by `pydub` to manipulate non-WAV audio formats (like MP3 or MP4).
    * **macOS:** `brew install ffmpeg`
    * **Linux (Ubuntu/Debian):** `sudo apt install ffmpeg`
    * **Windows:** `winget install ffmpeg` or download from the official site.

## 💻 Installation

1. Clone the repository:

    ```bash
    git clone https://github.com/yourusername/aitranscribe.git
    cd aitranscribe
    ```

2. Create and activate a virtual environment:

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the dependencies:

    ```bash
    pip install -r requirements.txt
    ```

4. Make the wrapper script executable and symlink it to your path so you can use it globally from anywhere:

    ```bash
    chmod +x aitranscribe
    sudo ln -s "$(pwd)/aitranscribe" /usr/local/bin/aitranscribe
    ```

## ⚙️ Configuration

`aitranscribe` uses a global configuration file to allow execution from any directory.

On the first run, the tool will automatically create a configuration template at:
`~/.config/aitranscribe/config`

1. Open the file using your favorite editor:

   ```bash
   nano ~/.config/aitranscribe/config
   ```

2. Add your Groq API key for STT and OpenRouter API key for LLM processing:

   ```env
   GROQ_API_KEY="your_groq_api_key_here"
   OPENROUTER_API_KEY="your_openrouter_api_key_here"
   GROQ_STT_MODEL="whisper-large-v3-turbo"
   OPENROUTER_LLM_MODEL="anthropic/claude-3-haiku"
   ```

## 🎯 Usage Examples

Because we symlinked `aitranscribe` to our global path, we can run it simply by typing `aitranscribe` from any directory on our system!

**Record from microphone (Default Mode, Push-to-Talk via Spacebar):**

```bash
aitranscribe
```

**Transcribe a local file:**

```bash
aitranscribe file path/to/audio.mp3
```

**Transcribe previous recording:**

```bash
# Running "file" without arguments defaults to /tmp/aitranscribe_record.mp3
aitranscribe file
```

**Transcribe a large file (auto-chunking applied automatically):**

```bash
aitranscribe file path/to/huge_podcast.mp3
```

**Transcribe and summarize using an LLM:**

```bash
aitranscribe file meeting.wav --post-process "Summarize this meeting and extract action items"
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

Or use `tox` to run them in an isolated environment.

## 🏗️ Code Architecture

The project follows clean code principles with focus on maintainability and testability:

* **Option Factory Pattern:** CLI options are defined through factory functions for consistency and reusability
* **Shared Logic Helpers:** Common operations are extracted into reusable utility functions
* **Comprehensive Testing:** All new functions include unit tests and integration tests
* **Single Source of Truth:** CLI parameters and shared logic are defined once, used everywhere

This architecture ensures that changes to shared functionality only need to be made in one place, reducing duplication and maintenance overhead.

## 📄 License

MIT License
