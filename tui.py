from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import textwrap
from typing import Any, Callable, Mapping

import numpy as np
import sounddevice as sd
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.events import Resize
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, OptionList, RadioButton, RadioSet, Static
from textual.widgets.option_list import Option


FeedbackCallback = Callable[[str, str], None]
ProcessAudioCallback = Callable[[np.ndarray, dict[str, Any], FeedbackCallback], dict[str, str]]


def get_clipboard_command(environ: Mapping[str, str] | None = None) -> list[str] | None:
    env = environ or os.environ

    if env.get("WAYLAND_DISPLAY") and shutil.which("wl-copy"):
        return ["wl-copy"]
    if env.get("DISPLAY") and shutil.which("xclip"):
        return ["xclip", "-selection", "clipboard"]
    if env.get("DISPLAY") and shutil.which("xsel"):
        return ["xsel", "--clipboard", "--input"]
    if shutil.which("pbcopy"):
        return ["pbcopy"]
    if shutil.which("clip.exe"):
        return ["clip.exe"]
    if shutil.which("clip"):
        return ["clip"]
    return None


def build_osc52_sequence(text: str, environ: Mapping[str, str] | None = None) -> str:
    payload = base64.b64encode(text.encode("utf-8")).decode("ascii")
    env = environ or os.environ
    sequence = f"\033]52;c;{payload}\a"

    if env.get("TMUX"):
        return f"\033Ptmux;\033{sequence}\033\\"
    return sequence


def copy_text_with_osc52(text: str, stream: Any = None, environ: Mapping[str, str] | None = None) -> bool:
    output = stream or sys.stdout
    if not hasattr(output, "write") or not hasattr(output, "flush"):
        return False

    env = environ or os.environ
    if not (env.get("TERM") or env.get("TERM_PROGRAM") or env.get("TMUX")):
        return False

    try:
        output.write(build_osc52_sequence(text, env))
        output.flush()
    except OSError:
        return False
    return True


def copy_text_to_clipboard(text: str) -> bool:
    command = get_clipboard_command()
    if command:
        try:
            subprocess.run(command, input=text, text=True, check=True)
            return True
        except (OSError, subprocess.SubprocessError):
            pass

    return copy_text_with_osc52(text)


class RecordingController:
    def __init__(self, samplerate: int = 44100, channels: int = 1) -> None:
        self.samplerate = samplerate
        self.channels = channels
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self.is_recording = False

    def _callback(self, indata: np.ndarray, frames: int, cb_time: Any, status: Any) -> None:
        del frames, cb_time, status
        if self.is_recording:
            self._chunks.append(indata.copy())

    def start(self) -> None:
        self._chunks = []
        self._stream = sd.InputStream(
            samplerate=self.samplerate,
            channels=self.channels,
            callback=self._callback,
        )
        self._stream.start()
        self.is_recording = True

    def stop(self) -> np.ndarray | None:
        self.is_recording = False
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        if not self._chunks:
            return None

        audio = np.concatenate(self._chunks, axis=0)
        self._chunks = []
        return audio


class AitranscribeTUI(App[None]):
    CSS = """
    Screen {
        layout: vertical;
        background: #0f1115;
        color: #f3f4f6;
    }

    Header {
        background: #1d3557;
        color: #f1faee;
    }

    Footer {
        background: #1d3557;
        color: #f1faee;
    }

    #body {
        height: 1fr;
        padding: 0 1;
    }

    #primary {
        width: 5fr;
        margin: 0 1 0 0;
    }

    #sidebar {
        width: 3fr;
        min-width: 42;
        margin: 0;
    }

    .panel {
        border: round #457b9d;
        background: #161a22;
        padding: 0 1;
        margin-bottom: 0;
    }

    #status_panel {
        height: 3;
        margin-bottom: 1;
    }

    #transcript_panel {
        height: 1fr;
        min-height: 10;
    }

    #feedback_panel {
        height: 6;
        margin-top: 1;
    }

    #history_panel {
        height: 11;
        margin-bottom: 1;
    }

    #history_summary {
        height: auto;
        color: #a8dadc;
        margin-bottom: 1;
    }

    #history_list {
        height: 1fr;
        margin-bottom: 1;
    }

    #config_panel,
    #extra_panel {
        height: auto;
    }

    #config_panel {
        margin-bottom: 1;
    }

    #history_actions {
        height: auto;
        margin-top: 0;
    }

    #mark_read {
        width: 100%;
    }

    Input {
        width: 100%;
        margin-bottom: 0;
    }

    .field_row {
        height: auto;
        margin-bottom: 1;
    }

    .field_row Label {
        width: 12;
        color: #a8dadc;
        content-align: left middle;
    }

    .field_row Input {
        width: 1fr;
    }

    .setting_box {
        height: auto;
        margin-top: 1;
    }

    .setting_box Checkbox {
        width: 100%;
        margin-bottom: 0;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_recording", "Record / Stop", priority=True),
        Binding("c", "copy_transcript", "Copy Transcript"),
        Binding("escape", "focus_recorder", "Recorder Focus"),
        Binding("m", "mark_all_read", "Mark Read"),
        Binding("q", "quit", "Quit"),
    ]

    FEEDBACK_STEPS = [
        ("stt_send", "Send Message to STT Provider"),
        ("stt_response", "Got Response from Whisper"),
        ("pre_send", "Sending to Pre-Processor"),
        ("pre_response", "Got Response from Pre-Processor"),
    ]

    INTERACTIVE_WIDGET_IDS = {
        "preprocess_modes",
        "stt_model",
        "llm_model",
        "cleanup_before_run",
        "store_history",
        "verbose_errors",
        "history_list",
        "mark_read",
    }

    def __init__(
        self,
        *,
        prompt_manager: Any,
        process_audio: ProcessAudioCallback,
        stt_provider_name: str,
        llm_provider_name: str,
        default_stt_model: str,
        default_llm_model: str,
    ) -> None:
        super().__init__()
        self.prompt_manager = prompt_manager
        self.process_audio = process_audio
        self.stt_provider_name = stt_provider_name
        self.llm_provider_name = llm_provider_name
        self.default_stt_model = default_stt_model
        self.default_llm_model = default_llm_model
        self.recorder = RecordingController()
        self.is_recording = False
        self.is_processing = False
        self.pre_process_mode = "raw"
        self.latest_transcript = "No transcript yet."
        self.history_prompts: list[dict[str, Any]] = []
        self.selected_history_id: int | None = None
        self.selected_history_text: str | None = None
        self.status_text = "Press Space to Start Recording"
        self.feedback_state = {step_id: "pending" for step_id, _ in self.FEEDBACK_STEPS}

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="primary"):
                yield Static(id="status_panel", classes="panel")
                with VerticalScroll(id="transcript_panel", classes="panel"):
                    yield Static(id="transcript_text")
                yield Static(id="feedback_panel", classes="panel")
            with Vertical(id="sidebar"):
                with Vertical(id="history_panel", classes="panel"):
                    yield Static(id="history_summary")
                    yield OptionList(id="history_list", compact=True)
                    with Vertical(id="history_actions"):
                        yield Button("Mark all transcriptions as read", id="mark_read", variant="primary")
                with Vertical(id="config_panel", classes="panel"):
                    with RadioSet(id="preprocess_modes"):
                        yield RadioButton("Raw transcription", id="mode-raw", value=True)
                        yield RadioButton("Clean up text", id="mode-cleanup")
                        yield RadioButton("Translate to English", id="mode-english")
                with Vertical(id="extra_panel", classes="panel"):
                    with Horizontal(classes="field_row"):
                        yield Label("STT Model")
                        yield Input(value=self.default_stt_model, placeholder=f"{self.stt_provider_name} model", id="stt_model")
                    with Horizontal(classes="field_row"):
                        yield Label("LLM Model")
                        yield Input(value=self.default_llm_model, placeholder=f"{self.llm_provider_name} model", id="llm_model")
                    with Vertical(classes="setting_box"):
                        yield Checkbox("Store transcriptions in queue", value=True, id="store_history")
                        yield Checkbox("Clean old temp recordings first", value=False, id="cleanup_before_run")
                        yield Checkbox("Verbose error output", value=False, id="verbose_errors")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#status_panel", Static).border_title = "Status"
        self.query_one("#transcript_panel", VerticalScroll).border_title = "Transcript (C to copy)"
        self.query_one("#feedback_panel", Static).border_title = "Feedback Log"
        self.query_one("#history_panel", Vertical).border_title = "Unread Transcriptions"
        self.query_one("#config_panel", Vertical).border_title = "Recording Mode"
        self.query_one("#extra_panel", Vertical).border_title = "Configuration"
        self.refresh_status()
        self.refresh_transcript()
        self.refresh_feedback()
        self.refresh_history()

    def refresh_status(self) -> None:
        hint = "Space=record | C=copy | Tab=config | Esc=record focus | Q=quit"
        self.query_one("#status_panel", Static).update(f"{self.status_text}\n{hint}")

    def _wrapped_text(self, text: str, width: int, preserve_lines: bool = False) -> str:
        effective_width = max(24, width)
        if preserve_lines:
            return "\n".join(
                textwrap.fill(line, width=effective_width) if line else ""
                for line in text.splitlines()
            )
        return textwrap.fill(text, width=effective_width)

    def get_displayed_transcript(self) -> str:
        if self.selected_history_text and not self.is_recording and not self.is_processing:
            return self.selected_history_text
        return self.latest_transcript

    def clear_history_selection(self) -> None:
        self.selected_history_id = None
        self.selected_history_text = None

    def select_history_prompt(self, index: int) -> None:
        if index < 0 or index >= len(self.history_prompts):
            return
        prompt = self.history_prompts[index]
        self.selected_history_id = int(prompt["id"])
        self.selected_history_text = str(prompt["prompt"])
        if self._screen_stack:
            self.refresh_transcript()

    def refresh_transcript(self) -> None:
        panel_width = self.query_one("#transcript_panel", VerticalScroll).size.width
        transcript = self.get_displayed_transcript()
        text = self._wrapped_text(transcript, panel_width - 4, preserve_lines=True) if transcript else ""
        self.query_one("#transcript_text", Static).update(text)

    def refresh_feedback(self) -> None:
        lines = []
        for step_id, label in self.FEEDBACK_STEPS:
            state = self.feedback_state[step_id]
            prefix = {
                "pending": "[ ]",
                "active": "[>]",
                "done": "[x]",
                "skipped": "[-]",
                "error": "[!]",
            }.get(state, "[ ]")
            lines.append(f"{prefix} {label}")
        self.query_one("#feedback_panel", Static).update("\n".join(lines))

    def refresh_history(self) -> None:
        count = self.prompt_manager.count_unplayed()
        history_list = self.query_one("#history_list", OptionList)
        panel_width = max(history_list.size.width, self.query_one("#history_panel", Vertical).size.width)
        snippet_width = max(28, panel_width - 8)
        self.history_prompts = self.prompt_manager.recent_prompts(limit=6)
        self.query_one("#history_summary", Static).update(f"Unread: {count} | Arrows to preview")

        if not self.history_prompts:
            self.clear_history_selection()
            history_list.set_options([Option("No unread transcriptions.", id="history-empty", disabled=True)])
            self.refresh_transcript()
            return

        options = []
        selected_index: int | None = None
        for index, prompt in enumerate(self.history_prompts):
            shortened = textwrap.shorten(prompt["prompt"].replace("\n", " "), width=snippet_width, placeholder="...")
            options.append(Option(f"#{prompt['id']}: {shortened}", id=f"history-{prompt['id']}"))
            if prompt["id"] == self.selected_history_id:
                selected_index = index

        history_list.set_options(options)
        if selected_index is not None:
            history_list.highlighted = selected_index
        elif self.selected_history_id is not None:
            self.clear_history_selection()
            self.refresh_transcript()

    def on_resize(self, event: Resize) -> None:
        del event
        self.refresh_status()
        self.refresh_transcript()
        self.refresh_feedback()
        self.refresh_history()

    def reset_feedback(self) -> None:
        self.feedback_state = {step_id: "pending" for step_id, _ in self.FEEDBACK_STEPS}
        self.refresh_feedback()

    def focus_is_interactive(self) -> bool:
        focused = self.focused
        return focused is not None and focused.id in self.INTERACTIVE_WIDGET_IDS

    def action_focus_recorder(self) -> None:
        self.screen.set_focus(None)
        if not self.is_recording and not self.is_processing:
            self.status_text = "Press Space to Start Recording"
            self.refresh_status()

    def action_toggle_recording(self) -> None:
        if self.is_processing:
            return

        if not self.is_recording and self.focus_is_interactive():
            return

        if self.is_recording:
            self.finish_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        try:
            self.recorder.start()
        except Exception as exc:
            self.status_text = f"Could not start recording: {exc}"
            self.refresh_status()
            return

        self.is_recording = True
        self.clear_history_selection()
        self.latest_transcript = "Recording in progress..."
        self.status_text = "Press Space again to Finish"
        self.reset_feedback()
        self.refresh_status()
        self.refresh_transcript()

    def finish_recording(self) -> None:
        audio = self.recorder.stop()
        self.is_recording = False
        if audio is None or len(audio) == 0:
            self.latest_transcript = "No audio recorded."
            self.status_text = "Press Space to Start Recording"
            self.refresh_transcript()
            self.refresh_status()
            return

        self.is_processing = True
        self.status_text = "Processing recording..."
        self.latest_transcript = "Waiting for transcription..."
        self.refresh_status()
        self.refresh_transcript()
        settings = self.collect_settings()
        self.run_worker(lambda: self.process_audio_worker(audio, settings), thread=True, exclusive=True)

    def collect_settings(self) -> dict[str, Any]:
        return {
            "pre_process_mode": self.pre_process_mode,
            "stt_model": self.query_one("#stt_model", Input).value.strip() or self.default_stt_model,
            "llm_model": self.query_one("#llm_model", Input).value.strip() or self.default_llm_model,
            "store_history": self.query_one("#store_history", Checkbox).value,
            "cleanup_before_run": self.query_one("#cleanup_before_run", Checkbox).value,
            "verbose": self.query_one("#verbose_errors", Checkbox).value,
        }

    def update_feedback_state(self, step_id: str, state: str) -> None:
        self.feedback_state[step_id] = state
        self.refresh_feedback()

    def process_audio_worker(self, audio: np.ndarray, settings: dict[str, Any]) -> None:
        def feedback(step_id: str, state: str) -> None:
            self.call_from_thread(self.update_feedback_state, step_id, state)

        try:
            result = self.process_audio(audio, settings, feedback)
        except Exception as exc:
            self.call_from_thread(self.processing_failed, str(exc))
            return

        self.call_from_thread(self.processing_finished, result)

    def processing_failed(self, error_message: str) -> None:
        self.is_processing = False
        self.clear_history_selection()
        for step_id, current in list(self.feedback_state.items()):
            if current == "active":
                self.feedback_state[step_id] = "error"
        self.latest_transcript = error_message
        self.status_text = "Processing failed. Press Space to try again."
        self.refresh_feedback()
        self.refresh_transcript()
        self.refresh_status()

    def processing_finished(self, result: dict[str, str]) -> None:
        self.is_processing = False
        self.clear_history_selection()
        self.latest_transcript = result.get("text", "") or "No transcript returned."
        self.status_text = "Press Space to Start Recording"
        self.refresh_transcript()
        self.refresh_status()
        self.refresh_history()

    def action_mark_all_read(self) -> None:
        marked = self.prompt_manager.mark_all_read()
        self.clear_history_selection()
        if marked:
            self.status_text = f"Marked {marked} transcription(s) as read."
        else:
            self.status_text = "Nothing to mark as read."
        self.refresh_status()
        self.refresh_transcript()
        self.refresh_history()

    def action_copy_transcript(self) -> None:
        text = self.get_displayed_transcript().strip()
        if not text or text in {"No transcript yet.", "Recording in progress...", "Waiting for transcription..."}:
            self.status_text = "No finished transcript to copy yet."
        elif copy_text_to_clipboard(text):
            self.status_text = "Copied transcript to clipboard."
        else:
            self.status_text = "Clipboard copy unavailable in this session."
        self.refresh_status()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "mark_read":
            self.action_mark_all_read()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id == "history_list":
            self.select_history_prompt(event.option_index)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "history_list":
            self.select_history_prompt(event.option_index)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "preprocess_modes" and event.pressed.id:
            self.pre_process_mode = event.pressed.id.removeprefix("mode-")
