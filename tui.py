from __future__ import annotations

import textwrap
from typing import Any, Callable

import numpy as np
import sounddevice as sd
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, RadioButton, RadioSet, Static, Switch


FeedbackCallback = Callable[[str, str], None]
ProcessAudioCallback = Callable[[np.ndarray, dict[str, Any], FeedbackCallback], dict[str, str]]


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
    }

    #primary {
        width: 2fr;
        margin: 1 1 1 1;
    }

    #sidebar {
        width: 1fr;
        margin: 1 1 1 0;
    }

    .panel {
        border: round #457b9d;
        background: #161a22;
        padding: 1 2;
        margin-bottom: 1;
    }

    #status_panel {
        height: 5;
    }

    #transcript_panel {
        height: 1fr;
        min-height: 14;
    }

    #feedback_panel {
        height: 8;
    }

    #history_panel {
        height: 14;
    }

    #config_panel,
    #extra_panel {
        height: auto;
    }

    #history_actions {
        height: auto;
        margin-top: 1;
    }

    #mark_read {
        width: 100%;
    }

    Label.section {
        color: #a8dadc;
        margin-bottom: 1;
        text-style: bold;
    }

    Input {
        width: 100%;
        margin-bottom: 1;
    }

    .setting_row {
        height: auto;
        margin-bottom: 1;
    }

    .setting_row Label {
        width: 1fr;
        content-align: left middle;
    }

    .setting_row Switch {
        dock: right;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_recording", "Record / Stop", priority=True),
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
                    yield Static(id="history_text")
                    with Vertical(id="history_actions"):
                        yield Button("Mark all transcriptions as read", id="mark_read", variant="primary")
                with Vertical(id="config_panel", classes="panel"):
                    yield Label("Pre-Processing", classes="section")
                    with RadioSet(id="preprocess_modes"):
                        yield RadioButton("Raw transcription", id="mode-raw", value=True)
                        yield RadioButton("Clean up text", id="mode-cleanup")
                        yield RadioButton("Translate to English", id="mode-english")
                with Vertical(id="extra_panel", classes="panel"):
                    yield Label("Additional Settings", classes="section")
                    yield Label(f"STT Provider: {self.stt_provider_name}")
                    yield Input(value=self.default_stt_model, placeholder="STT model", id="stt_model")
                    yield Label(f"LLM Provider: {self.llm_provider_name}")
                    yield Input(value=self.default_llm_model, placeholder="LLM model", id="llm_model")
                    with Horizontal(classes="setting_row"):
                        yield Label("Store transcriptions in queue")
                        yield Switch(value=True, id="store_history")
                    with Horizontal(classes="setting_row"):
                        yield Label("Clean old temp recordings first")
                        yield Switch(value=False, id="cleanup_before_run")
                    with Horizontal(classes="setting_row"):
                        yield Label("Verbose error output")
                        yield Switch(value=False, id="verbose_errors")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#status_panel", Static).border_title = "Status"
        self.query_one("#transcript_panel", VerticalScroll).border_title = "Transcript"
        self.query_one("#feedback_panel", Static).border_title = "Feedback Log"
        self.query_one("#history_panel", Vertical).border_title = "Unread Transcriptions"
        self.query_one("#config_panel", Vertical).border_title = "Recording Mode"
        self.query_one("#extra_panel", Vertical).border_title = "Configuration"
        self.refresh_status()
        self.refresh_transcript()
        self.refresh_feedback()
        self.refresh_history()

    def refresh_status(self) -> None:
        hint = "Press Q to quit. Use Tab for config controls, Esc to return to recording."
        self.query_one("#status_panel", Static).update(f"{self.status_text}\n{hint}")

    def refresh_transcript(self) -> None:
        text = textwrap.fill(self.latest_transcript, width=68) if self.latest_transcript else ""
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
        recent = self.prompt_manager.recent_prompts(limit=4)
        if not recent:
            body = "No unread transcriptions."
        else:
            snippets = []
            for prompt in recent:
                shortened = textwrap.shorten(prompt["prompt"].replace("\n", " "), width=84, placeholder="...")
                snippets.append(f"#{prompt['id']}: {shortened}")
            body = "\n".join(snippets)
        self.query_one("#history_text", Static).update(f"Unread: {count}\n\n{body}")

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
            "store_history": self.query_one("#store_history", Switch).value,
            "cleanup_before_run": self.query_one("#cleanup_before_run", Switch).value,
            "verbose": self.query_one("#verbose_errors", Switch).value,
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
        self.latest_transcript = result.get("text", "") or "No transcript returned."
        self.status_text = "Press Space to Start Recording"
        self.refresh_transcript()
        self.refresh_status()
        self.refresh_history()

    def action_mark_all_read(self) -> None:
        marked = self.prompt_manager.mark_all_read()
        if marked:
            self.status_text = f"Marked {marked} transcription(s) as read."
        else:
            self.status_text = "Nothing to mark as read."
        self.refresh_status()
        self.refresh_history()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "mark_read":
            self.action_mark_all_read()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "preprocess_modes" and event.pressed.id:
            self.pre_process_mode = event.pressed.id.removeprefix("mode-")
