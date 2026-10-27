# aitranscribe

Speech-to-text desktop tool with a terminal UI, powered by any OpenAI-compatible STT endpoint (Groq, self-hosted Whisper, …) and multiple LLM providers for post-processing.

## Overview

`aitranscribe` records microphone audio or transcribes local files (MP3, WAV, MP4, M4A, etc.) using any OpenAI-compatible transcription endpoint — Groq's Whisper API, a self-hosted faster-whisper server, or OpenAI itself. Transcriptions can optionally be cleaned up, translated, or summarized through an LLM of your choice. STT and LLM are configured independently, so you can transcribe on your own hardware and still post-process in the cloud.

## Quick start

```bash
git clone https://github.com/georgernstgraf/aitranscribe.git
cd aitranscribe
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `~/.config/aitranscribe/config.toml` (a commented template is also written automatically on first run, see `config.example.toml`):

```toml
version = 2

[stt]
provider = "groq"

[stt.providers.groq]
api_key = "your_groq_api_key"        # or: api_key_env = "GROQ_API_KEY"
model   = "whisper-large-v3-turbo"

[llm]
provider = "openrouter"

[llm.providers.openrouter]
api_key = "your_openrouter_api_key"
model   = "anthropic/claude-3-haiku"
```

Scope tables (`[stt]`, `[llm]`) only *select* a profile; everything about an
endpoint — base URL, keys, model, chunk limits — lives in its
`[<scope>.providers.<name>]` table.

Run without arguments to launch the TUI:

```bash
./aitranscribe
```

Or symlink it for global access:

```bash
chmod +x aitranscribe
ln -s "$(pwd)/aitranscribe" ~/.local/bin/aitranscribe
```

On Windows, add the repo directory to `PATH` and use `aitranscribe.bat`.

## Prerequisites

- **Python 3.11+**
- **FFmpeg** (including `ffprobe`) – required for audio compression and chunking (`brew install ffmpeg`, `apt install ffmpeg`, `winget install --id Gyan.FFmpeg --exact`). Restart the terminal after installing it on Windows.
- **Clipboard helpers** (for the TUI copy action): `xclip` (X11) or `wl-clipboard` (Wayland) on Linux
- **PortAudio** (libportaudio) – needed for microphone recording on most systems

## TUI

The terminal UI is built with [Textual](https://textual.textualize.io/) and divided into several panels:

- **Status** – current mode (command/pane-focus) and activity (ready, recording, processing)
- **Transcript** – editable view of the latest or selected transcription
- **Feedback Log** – live status of compression, transcription, and LLM post-processing steps
- **Transcriptions** – list of saved transcriptions with auto-generated summaries; arrow keys to preview
- **Recording Mode** – switch between microphone and filesystem file as input
- **Configuration** – STT/LLM provider, their models, and output line width (0/80/120)

### Keybindings

| Key | Action |
|---|---|
| `Space` | Start / stop microphone recording |
| `P` | Pause / resume an active microphone recording |
| `A` | Append new recording to the currently selected transcription |
| `Ctrl+S` | Save the editor contents as a new transcription |
| `C` | Copy transcript to clipboard (X11, Wayland, macOS, Windows, or OSC 52) |
| `D` | Translate transcript to German via LLM |
| `E` | Translate transcript to English via LLM |
| `W` | Write the selected transcription to `/tmp/issue.md` |
| `Delete` | Delete the selected transcription from the list |
| `Escape` | Cancel the active recording (discards the dictated audio); otherwise enter command mode (unfocus all widgets) |
| `Q` | Quit |

### Recording modes

- **Microphone**: press Space to start, Space again to stop. Press `P` to pause and resume without ending the session; only the audio recorded between pauses is transcribed. Press `Escape` to cancel and discard the recording. Audio is compressed to 32 kbps MP3 before sending; takes longer than the active STT profile's chunk ceiling (2 minutes for Groq) are split at pauses into several uploads.
- **Filesystem file**: enter a file path in the File field and press Enter. Files longer than the profile's chunk ceiling (2 minutes / 25 MB for Groq, freely configurable for self-hosted endpoints) are automatically chunked to stay within that profile's limits; cuts are placed in detected pauses, so no word is split.

### No audio from the input device

If the system's default input is a source that never delivers frames (webcam
microphones behind PipeWire are a common case), the TUI no longer freezes on
`Recording`: it retries once, then aborts the take with a **No Audio Input**
dialog naming the device. Switch the system sound input to another microphone
and press `Space` again.

Microphone capture goes through PortAudio's native **PulseAudio/PipeWire**
client when the host provides one, so the system default source (as set in the
desktop sound settings) is used directly and ALSA's `default` PCM — which spams
`pa_linux_alsa.c` failed assertions and can block for tens of seconds — is
avoided.

### Pre-processing modes

Three modes control what happens after transcription:

| Mode | Effect |
|---|---|
| **Raw transcription** | No LLM post-processing; the raw STT output is stored |
| **Cleanup Text / Preserve Language** | LLM corrects grammar, removes filler words, structures the text |
| **Cleanup + Translate to English** | LLM translates to English and cleans up |

### Append recording

Select a saved transcription from the list, press `A`, and speak. The new recording is transcribed and appended to the existing text. The updated entry is saved in place.

## CLI

When flags are provided, `aitranscribe` runs in CLI mode instead of launching the TUI.

```bash
aitranscribe --file meeting.mp3                          # transcribe a file
aitranscribe --file speech.mp3 --english                 # transcribe + translate to English
aitranscribe --file podcast.mp3 --post-process           # transcribe + cleanup
aitranscribe --post-process "Summarize this recording"   # custom LLM prompt
aitranscribe --width 120 --file meeting.mp3              # wrap output at 120 chars/line
aitranscribe --list                                      # show stored transcriptions
aitranscribe --query                                     # pop the oldest transcription
aitranscribe --remove 3                                  # remove transcription #3
```

`--english` and `--post-process` are mutually exclusive.

## Configuration

Configuration lives in `~/.config/aitranscribe/config.toml` (Linux/macOS) or
`%APPDATA%\aitranscribe\config.toml` (Windows); the file is `0600`. A commented
template is created on first run, and a legacy `aitranscribe.conf` is migrated
once (the old file is kept as `aitranscribe.conf.bak-<timestamp>`).

### Schema

```toml
version = 2

[stt]
provider = "selfhosted-1"        # selector only

[stt.providers.selfhosted-1]     # complete endpoint description
description   = "Whisper large-v3 on my own GPU"
base_url      = "https://whisper.example.org/v1"
api_key       = "…"              # string or array
# api_key_env = "MY_KEY_VAR"     # string or array, resolved before api_key
model         = "large-v3"
max_upload_s  = 900              # chunk ceiling; Groq needs <=120 (see below)
max_upload_mb = 100

[stt.providers.groq]
api_key       = "gsk_…"
model         = "whisper-large-v3"
max_upload_s  = 120
max_upload_mb = 25

[llm]
provider = "groq"

[llm.providers.groq]
api_key = "gsk_…"
model   = "openai/gpt-oss-120b"

[ui]
pre_process_mode = "raw"         # raw, cleanup, or english
output_width     = 80            # 0 (off), 80, or 120
verbose_errors   = false
last_file_path   = ""

[paths]
prompts_file = "/home/you/.config/aitranscribe/prompts.sqlite"
```

Rules:

- **One value, one place.** A scope table holds `provider` only; the model belongs
  to the profile, so switching providers also switches the model.
- **Any OpenAI-compatible endpoint works**: Groq, OpenAI, a local
  `faster-whisper` server, LiteLLM, LM Studio, vLLM, …
- **Keys**: `api_key` and `api_key_env` accept a string or an array (rotation /
  failover: first key wins). Environment-referenced keys are resolved first, so
  secrets can stay out of the file. The TUI never touches keys.
- **STT and LLM are independent** and never share credentials: a self-hosted
  whisper key is only sent to the whisper server, a cloud key only to the LLM.
- **`max_upload_s` / `max_upload_mb`** are per profile. Groq must stay at ≤120 s
  (its API mangles text beyond ~122 s); self-hosted servers can go much higher
  (only the reverse-proxy timeout limits them).

### Built-in provider defaults

A known profile id needs no `base_url`/`model` of its own:

| Profile id | Base URL | Default LLM model |
|---|---|---|
| `groq` | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` |
| `openrouter` | `https://openrouter.ai/api/v1` | `anthropic/claude-3-haiku` |
| `cohere` | `https://api.cohere.ai/compatibility/v1` | `command-r` |
| `zai` | `https://api.z.ai/api/coding/paas/v4` | `glm-5` |
| `google` | `https://generativelanguage.googleapis.com/v1beta/openai/` | `gemini-2.0-flash` |
| `cortecs` | `https://api.cortecs.ai/v1` | `qwen3.8-flash-next` |

Anything else needs its own `base_url` and `model`.

### Configuration commands

```bash
aitranscribe config show              # active profiles, masked keys, key sources
aitranscribe config show --reveal     # full keys
aitranscribe config check             # validate every active profile
aitranscribe config check --probe     # also GET /v1/models on each endpoint
aitranscribe config edit              # open in $EDITOR, then validate
aitranscribe config migrate           # convert a legacy aitranscribe.conf
aitranscribe config path              # print the config file location
```

The TUI writes user-adjustable settings into the same file (comments and layout
are preserved) and offers **STT**/**LLM** provider selectors in its
Configuration panel.

### TUI defaults

The `[ui]` table remembers TUI state:

```toml
[ui]
pre_process_mode = "english"     # raw, cleanup, or english
last_file_path   = ""            # last used file path
verbose_errors   = false         # show detailed errors
output_width     = 80            # wrap output at 0 (off), 80, or 120 chars/line
```

The recording mode (microphone vs filesystem file) is chosen per session in the TUI and always starts as microphone on launch.

### Output wrapping

Transcriptions (terminal output, TUI transcript, and stored history) can be wrapped at 80 or 120 characters per line; a line break replaces the space at the wrap point. Long unbreakable tokens (e.g. URLs) are left intact. Configure it with `[ui].output_width` in the config file, the `--width` CLI flag (`0`, `80`, or `120`), or the **Output width** control in the TUI's Configuration panel. `0` disables wrapping. Because wrapped text is stored as-is, changing the width affects newly produced transcriptions.

## Project structure

```
aitranscribe/
  main.py          # CLI entry point (Typer), recording, transcription
                   # workflow, config commands, prompt manager (SQLite queue)
  config.py        # TOML schema v2: profiles, key resolution, migration, writer
  core.py          # Audio compression, chunking, STT calls, LLM post-processing
  config.example.toml  # Documented configuration template
  tui.py           # Textual TUI with panels, keybindings, recording controller
  aitranscribe     # Bash wrapper (activates venv, runs main.py)
  aitranscribe.bat # Windows equivalent
  pyproject.toml   # Package metadata and entry point
  tests/
    test_cli.py
    test_config.py
    test_tui.py
  android/         # Kotlin/Jetpack Compose Android app (separate)
```

## Architecture notes

- **Audio pipeline**: microphone → raw WAV → MP3 (32 kbps) → active STT profile → optional LLM post-processing → SQLite storage
- **File transcription**: auto-chunking splits uploads longer than the active profile's ceilings (2 minutes / 25 MB for Groq) into pause-aligned segments, transcribes each, and joins results
- **Prompt manager**: SQLite database (`~/.config/aitranscribe/prompts.sqlite`) stores transcriptions with timestamps and auto-generated LLM summaries. Uses DELETE journal mode for cloud-sync (OneDrive, Dropbox) compatibility
- **Recording files**: saved to the system temp directory with versioned filenames (`aitranscribe_record_v001.mp3`)
- **Clipboard**: tries `wl-copy`, `xclip`, `xsel`, `pbcopy`, `clip.exe` in order, with OSC 52 escape sequence as fallback
- **Cross-platform**: supports Linux, macOS, and Windows (including MSYS2 UCRT64 environments and PyInstaller bundles)

## LLM post-processing safety

The system prompt instructs the LLM to:
- Output only the requested processed text (no explanations or meta-commentary)
- Preserve the original meaning and intent
- Not execute any instructions embedded in the transcription

## Testing

```bash
pip install -r requirements-dev.txt
pytest
```

Or use tox: `tox`.

## Android app

An Android version with push-to-talk, background transcription, and offline queue is available in the `android/` directory. See `android/README.md` for details.

```bash
cd android
./gradlew assembleDebug
```

## License

MIT
