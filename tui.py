from __future__ import annotations

import base64
import os
import shutil
import subprocess
import sys
import textwrap
from typing import Any, Callable, Mapping

import numpy as np
from rich.text import Text
import sounddevice as sd
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Resize
from textual.message import Message
from textual.widgets import Footer, Header, Input, Label, OptionList, RadioButton, RadioSet, Static, TextArea
from textual.widgets.option_list import Option


FeedbackCallback = Callable[[str, str], None]
TranscriptCallback = Callable[[str], None]
ProcessAudioCallback = Callable[[np.ndarray, dict[str, Any], FeedbackCallback, TranscriptCallback], dict[str, Any]]
ProcessFileCallback = Callable[[str, dict[str, Any], FeedbackCallback, TranscriptCallback], dict[str, Any]]
GenerateSummaryCallback = Callable[[str, str], str | None]
BackfillSummariesCallback = Callable[[], int]


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
        align: left top;
    }

    #primary {
        width: 4fr;
        height: 1fr;
        margin: 0 1 0 0;
        layout: vertical;
    }

    #sidebar {
        width: 3fr;
        height: 1fr;
        min-width: 42;
        margin: 0;
        layout: vertical;
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

    #status_row {
        height: 1;
    }

    #state_status {
        width: 1fr;
    }

    #flash_status {
        width: 1fr;
        color: #a8dadc;
    }

    #transcript_panel {
        height: 1fr;
        min-height: 10;
    }

    #transcript_editor {
        height: 1fr;
        border: none;
        background: transparent;
        padding: 0;
    }

    #feedback_panel {
        height: 6;
        margin-top: 1;
    }

    #history_panel {
        height: 1fr;
        min-height: 11;
        margin-bottom: 1;
    }

    #history_summary {
        height: auto;
        color: #a8dadc;
        margin-bottom: 1;
    }

    #history_list {
        height: 1fr;
        margin-bottom: 0;
    }

    #config_panel,
    #extra_panel {
        height: auto;
    }

    #extra_panel {
        margin-top: 0;
    }

    #config_panel {
        margin-bottom: 1;
    }

    Input {
        width: 100%;
        margin-bottom: 0;
    }

    .field_row {
        height: 3;
        margin-bottom: 0;
        align: center middle;
    }

    .field_row Label {
        width: 11;
        color: #a8dadc;
        content-align: left middle;
        padding-top: 1;
    }

    .field_row Input {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_recording", "Record / Stop", priority=True),
        Binding("a", "append_recording", "Append Recording"),
        Binding("ctrl+s", "save_transcript", "Save Transcript"),
        Binding("c", "copy_transcript", "Copy Transcript"),
        Binding("w", "write_issue", "Write Issue File"),
        Binding("delete", "delete_selected_transcription", "Delete Selected"),
        Binding("escape", "enter_command_mode", "Command Mode"),
        Binding("q", "quit", "Quit"),
    ]

    FEEDBACK_STEPS = [
        ("compress", "Compressing Message"),
        ("transcribe", "Transcribing Raw Message"),
        ("post_process", "Post-Processing Message"),
        ("summary", "Creating Summary"),
    ]

    PANE_FOCUS_WIDGET_IDS = {
        "source_modes",
        "preprocess_modes",
        "file_path",
        "stt_model",
        "llm_model",
        "transcript_editor",
        "history_list",
    }

    def __init__(
        self,
        *,
        prompt_manager: Any,
        process_audio: ProcessAudioCallback,
        process_file: ProcessFileCallback,
        stt_provider_name: str,
        llm_provider_name: str,
        default_stt_model: str,
        default_llm_model: str,
        initial_settings: dict[str, Any] | None = None,
        persist_setting: Callable[[str, Any], None] | None = None,
        generate_summary: GenerateSummaryCallback | None = None,
        backfill_summaries: BackfillSummariesCallback | None = None,
    ) -> None:
        super().__init__()
        self.prompt_manager = prompt_manager
        self.process_audio = process_audio
        self.process_file = process_file
        self.persist_setting = persist_setting
        self.generate_summary = generate_summary
        self.backfill_summaries = backfill_summaries
        self.stt_provider_name = stt_provider_name
        self.llm_provider_name = llm_provider_name
        self.default_stt_model = default_stt_model
        self.default_llm_model = default_llm_model
        self.initial_settings = initial_settings or {}
        self.recorder = RecordingController()
        self.is_recording = False
        self.is_processing = False
        self.input_source = str(self.initial_settings.get("input_source", "microphone"))
        self.pre_process_mode = str(self.initial_settings.get("pre_process_mode", "english"))
        self.verbose = bool(self.initial_settings.get("verbose", False))
        self.latest_transcript = "No transcript yet."
        self.history_prompts: list[dict[str, Any]] = []
        self.selected_history_id: int | None = None
        self.selected_history_text: str | None = None
        self.selected_history_filename: str | None = None
        self.latest_file_path: str | None = None
        self.status_text = "Press Space to Start Recording" if self.input_source == "microphone" else "Press Enter on File to Transcribe"
        self.feedback_state = {step_id: "pending" for step_id, _ in self.FEEDBACK_STEPS}
        self.raw_transcript: str | None = None
        self.append_mode: bool = False
        self.append_target_id: int | None = None
        self.append_base_text: str = ""
        self.flash_message = ""

    class FocusModeChanged(Message):
        def __init__(self) -> None:
            super().__init__()

    def current_mode_label(self) -> str:
        return "Pane Focus Mode" if self.is_pane_focus_mode() else "Command Mode"

    def current_activity_label(self) -> str:
        if self.is_recording:
            if self.append_mode:
                return "Appending"
            return "Recording"
        if self.is_processing:
            if self.append_mode:
                return "Appending"
            if self.input_source == "file":
                return "Processing File"
            return "Processing Recording"
        if self.input_source == "file":
            return "Ready for File"
        return "Ready"

    def current_state_label(self) -> str:
        mode_label = self.current_mode_label()
        activity_label = self.current_activity_label()
        if self.is_recording:
            activity_label = f"{activity_label}: Press Space to Finish"
        return f"{mode_label} | {activity_label}"

    def set_flash_message(self, message: str) -> None:
        self.flash_message = message

    def clear_flash_message(self) -> None:
        self.flash_message = ""

    def refresh_flash(self) -> None:
        self.query_one("#flash_status", Static).update(self.flash_message)

    def refresh_state(self) -> None:
        self.query_one("#state_status", Static).update(self.current_state_label())

    def refresh_status_panel(self) -> None:
        self.refresh_state()
        self.refresh_flash()

    def set_status_message(self, message: str) -> None:
        self.status_text = message
        self.set_flash_message(message)

    def set_idle_status(self) -> None:
        self.status_text = "Press Space to Start Recording" if self.input_source == "microphone" else "Press Enter on File to Transcribe"

    def set_processing_status(self) -> None:
        self.status_text = "Processing recording..." if self.input_source == "microphone" else "Processing file..."

    def start_operation_feedback(self) -> None:
        self.clear_flash_message()

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="body"):
            with Vertical(id="primary"):
                with Vertical(id="status_panel", classes="panel"):
                    with Horizontal(id="status_row"):
                        yield Static(id="state_status")
                        yield Static(id="flash_status")
                with Vertical(id="transcript_panel", classes="panel"):
                    yield TextArea("No transcript yet.", id="transcript_editor")
                yield Static(id="feedback_panel", classes="panel")
            with Vertical(id="sidebar"):
                with Vertical(id="history_panel", classes="panel"):
                    yield Static(id="history_summary")
                    yield OptionList(id="history_list", compact=True)
                with Vertical(id="config_panel", classes="panel"):
                    with RadioSet(id="source_modes"):
                        yield RadioButton("Microphone", id="source-microphone", value=self.input_source == "microphone")
                        yield RadioButton("Filesystem file", id="source-file", value=self.input_source == "file")
                    with Horizontal(classes="field_row"):
                        yield Label("File")
                        yield Input(value=str(self.initial_settings.get("file_path", "")), placeholder="/path/to/audio.mp3", id="file_path")
                    with RadioSet(id="preprocess_modes"):
                        yield RadioButton("Raw transcription", id="mode-raw", value=self.pre_process_mode == "raw")
                        yield RadioButton("Cleanup Text / Preserve Language", id="mode-cleanup", value=self.pre_process_mode == "cleanup")
                        yield RadioButton("Cleanup + Translate to English", id="mode-english", value=self.pre_process_mode == "english")
                with Vertical(id="extra_panel", classes="panel"):
                    with Horizontal(classes="field_row"):
                        yield Label("STT-Model")
                        yield Input(value=self.default_stt_model, placeholder=f"{self.stt_provider_name} model", id="stt_model")
                    with Horizontal(classes="field_row"):
                        yield Label("LLM-Model")
                        yield Input(value=self.default_llm_model, placeholder=f"{self.llm_provider_name} model", id="llm_model")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#status_panel", Vertical).border_title = "Status"
        self.query_one("#transcript_panel", Vertical).border_title = "Transcript (editable, Ctrl+S to save)"
        self.query_one("#feedback_panel", Static).border_title = "Feedback Log"
        self.query_one("#history_panel", Vertical).border_title = "Transcriptions"
        self.query_one("#config_panel", Vertical).border_title = "Recording Mode"
        self.query_one("#extra_panel", Vertical).border_title = "Configuration"
        self.refresh_status()
        self.refresh_transcript()
        self.refresh_feedback()
        self.refresh_history()
        self.call_after_refresh(self.refresh_history)
        self._focus_initial_widget()
        if self.backfill_summaries is not None:
            self.run_worker(self.backfill_summaries_worker, thread=True, exclusive=False)

    def refresh_status(self) -> None:
        self.refresh_status_panel()

    def _focus_initial_widget(self) -> None:
        if self.input_source == "file":
            self.set_focus(self.query_one("#file_path", Input))
            return

        history_list = self.query_one("#history_list", OptionList)
        self.set_focus(history_list)
        if self.history_prompts:
            history_list.highlighted = 0
            self.select_history_prompt(0)

    def get_displayed_transcript(self) -> str:
        if self.selected_history_text and not self.is_recording and not self.is_processing:
            return self.selected_history_text
        return self.latest_transcript

    def get_transcript_editor(self) -> TextArea:
        return self.query_one("#transcript_editor", TextArea)

    def get_editor_text(self) -> str:
        return self.get_transcript_editor().text

    def set_editor_text(self, text: str) -> None:
        self.get_transcript_editor().text = text

    def clear_history_selection(self) -> None:
        self.selected_history_id = None
        self.selected_history_text = None
        self.selected_history_filename = None

    def cancel_append_mode(self) -> None:
        self.append_mode = False
        self.append_target_id = None
        self.append_base_text = ""

    def select_history_prompt(self, index: int) -> None:
        if index < 0 or index >= len(self.history_prompts):
            return
        prompt = self.history_prompts[index]
        self.selected_history_id = int(prompt["id"])
        self.selected_history_text = str(prompt["prompt"])
        filename = prompt.get("filename")
        self.selected_history_filename = str(filename) if filename is not None else None
        if self._screen_stack:
            self.refresh_transcript()

    def refresh_transcript(self) -> None:
        self.set_editor_text(self.get_displayed_transcript())

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
        self.query_one("#feedback_panel", Static).update(Text("\n".join(lines), no_wrap=True, overflow="crop"))

    def refresh_history(self) -> None:
        count = self.prompt_manager.count_prompts()
        history_list = self.query_one("#history_list", OptionList)
        available_width = self._history_preview_width()
        self.history_prompts = self.prompt_manager.recent_prompts()
        self.query_one("#history_summary", Static).update(f"Stored: {count} | Arrows to preview")

        if not self.history_prompts:
            self.clear_history_selection()
            history_list.set_options([Option("No transcriptions yet.", id="history-empty", disabled=True)])
            self.refresh_transcript()
            return

        options = []
        selected_index: int | None = None
        for index, prompt in enumerate(self.history_prompts):
            summary_text = str(prompt.get("summary") or "").strip()
            preview_source = summary_text or str(prompt["prompt"])
            prefix = f"#{prompt['id']}: "
            text_width = max(8, available_width - len(prefix))
            shortened = textwrap.shorten(preview_source.replace("\n", " "), width=text_width, placeholder=" ...")
            options.append(Option(f"#{prompt['id']}: {shortened}", id=f"history-{prompt['id']}"))
            if prompt["id"] == self.selected_history_id:
                selected_index = index

        history_list.set_options(options)
        if selected_index is not None:
            history_list.highlighted = selected_index
            self.select_history_prompt(selected_index)
        else:
            if history_list.highlighted is None or history_list.highlighted >= len(options):
                history_list.highlighted = 0
            self.select_history_prompt(history_list.highlighted)

    def _history_preview_width(self) -> int:
        history_list = self.query_one("#history_list", OptionList)
        history_panel = self.query_one("#history_panel", Vertical)
        width_candidates = [
            history_list.content_region.width,
            history_list.scrollable_content_region.width,
            history_list.size.width,
            history_panel.content_region.width,
            history_panel.size.width,
        ]
        concrete_widths = [width for width in width_candidates if width > 0]
        if not concrete_widths:
            return 72
        return max(12, max(concrete_widths) - 6)

    def on_resize(self, event: Resize) -> None:
        del event
        self.refresh_status()
        self.refresh_feedback()
        self.refresh_history()

    def reset_feedback(self) -> None:
        self.feedback_state = {step_id: "pending" for step_id, _ in self.FEEDBACK_STEPS}
        self.refresh_feedback()

    def is_pane_focus_mode(self) -> bool:
        focused = self.focused
        return focused is not None and focused.id in self.PANE_FOCUS_WIDGET_IDS

    def is_command_mode(self) -> bool:
        return not self.is_pane_focus_mode()

    def action_enter_command_mode(self) -> None:
        self.screen.set_focus(None)
        if not self.is_recording and not self.is_processing:
            self.set_idle_status()
        self.refresh_status()

    def watch_focus(self, old_focus: Any, new_focus: Any) -> None:
        del old_focus, new_focus
        if self.is_mounted:
            self.post_message(self.FocusModeChanged())

    def on_descendant_focus(self) -> None:
        if self.is_mounted:
            self.refresh_status()

    def on_descendant_blur(self) -> None:
        if self.is_mounted:
            self.refresh_status()

    def on_aitranscribe_tui_focus_mode_changed(self, event: FocusModeChanged) -> None:
        del event
        self.refresh_status()

    def action_toggle_recording(self) -> None:
        if self.is_processing:
            return

        if self.input_source == "file":
            return

        if not self.is_recording and self.is_pane_focus_mode():
            return

        if self.is_recording:
            self.finish_recording()
        else:
            self.start_recording()

    def action_append_recording(self) -> None:
        if self.is_processing:
            return

        if self.input_source == "file":
            return

        if not self.is_recording and self.is_pane_focus_mode():
            return

        if self.selected_history_id is None or self.selected_history_text is None:
            self.cancel_append_mode()
            self.set_status_message("Select a saved transcription before appending.")
            self.refresh_status()
            return

        self.append_target_id = self.selected_history_id
        self.append_base_text = self.selected_history_text
        self.latest_transcript = self.append_base_text
        self.append_mode = True
        self.start_recording()

    def start_recording(self) -> None:
        try:
            self.recorder.start()
        except Exception as exc:
            self.set_status_message(f"Could not start recording: {exc}")
            self.refresh_status()
            return

        self.is_recording = True
        if not self.append_mode:
            self.clear_history_selection()
        self.latest_file_path = None
        self.raw_transcript = None
        if self.append_mode and self.append_base_text:
            self.latest_transcript = self.append_base_text
        elif not self.append_mode:
            self.latest_transcript = "Recording in progress..."
        self.start_operation_feedback()
        self.reset_feedback()
        self.refresh_status()
        self.refresh_transcript()

    def finish_recording(self) -> None:
        audio = self.recorder.stop()
        self.is_recording = False
        if audio is None or len(audio) == 0:
            self.cancel_append_mode()
            self.latest_transcript = "No audio recorded."
            self.latest_file_path = None
            self.set_status_message("No audio recorded.")
            self.refresh_transcript()
            self.refresh_status()
            return

        self.is_processing = True
        self.raw_transcript = None
        self.start_operation_feedback()
        self.set_processing_status()
        self.latest_transcript = "Waiting for transcription..."
        self.refresh_status()
        self.refresh_transcript()
        settings = self.collect_settings()
        self.run_worker(lambda: self.process_audio_worker(audio, settings), thread=True, exclusive=True)

    def start_file_transcription(self) -> None:
        file_path = self.query_one("#file_path", Input).value.strip()
        if not file_path:
            self.set_status_message("Enter an audio file path first.")
            self.refresh_status()
            return

        self.is_processing = True
        self.clear_history_selection()
        self.raw_transcript = None
        self.latest_transcript = f"Transcribing file: {file_path}"
        self.latest_file_path = file_path
        self.start_operation_feedback()
        self.set_processing_status()
        self.reset_feedback()
        self.refresh_status()
        self.refresh_transcript()
        settings = self.collect_settings()
        self.run_worker(lambda: self.process_file_worker(file_path, settings), thread=True, exclusive=True)

    def collect_settings(self) -> dict[str, Any]:
        return {
            "input_source": self.input_source,
            "file_path": self.query_one("#file_path", Input).value.strip(),
            "pre_process_mode": self.pre_process_mode,
            "stt_model": self.query_one("#stt_model", Input).value.strip() or self.default_stt_model,
            "llm_model": self.query_one("#llm_model", Input).value.strip() or self.default_llm_model,
            "verbose": self.verbose,
        }

    def persist_setting_value(self, setting_name: str, value: Any) -> None:
        if self.persist_setting is not None:
            self.persist_setting(setting_name, value)

    def update_feedback_state(self, step_id: str, state: str) -> None:
        self.feedback_state[step_id] = state
        self.refresh_feedback()

    def update_transcript_from_worker(self, text: str) -> None:
        self.raw_transcript = text
        if self.append_mode:
            if self.append_base_text:
                self.latest_transcript = self.append_base_text.rstrip() + "\n\n" + (text or "")
            else:
                self.latest_transcript = text or "No transcript returned."
        else:
            self.latest_transcript = text or "No transcript returned."
        self.refresh_transcript()

    def process_audio_worker(self, audio: np.ndarray, settings: dict[str, Any]) -> None:
        def feedback(step_id: str, state: str) -> None:
            self.call_from_thread(self.update_feedback_state, step_id, state)

        def transcript_callback(text: str) -> None:
            self.call_from_thread(self.update_transcript_from_worker, text)

        try:
            result = self.process_audio(audio, settings, feedback, transcript_callback)
        except Exception as exc:
            self.call_from_thread(self.processing_failed, str(exc))
            return

        self.call_from_thread(self.processing_finished, result)

    def process_file_worker(self, file_path: str, settings: dict[str, Any]) -> None:
        def feedback(step_id: str, state: str) -> None:
            self.call_from_thread(self.update_feedback_state, step_id, state)

        def transcript_callback(text: str) -> None:
            self.call_from_thread(self.update_transcript_from_worker, text)

        try:
            result = self.process_file(file_path, settings, feedback, transcript_callback)
        except Exception as exc:
            self.call_from_thread(self.processing_failed, str(exc))
            return

        self.call_from_thread(self.processing_finished, result)

    def processing_failed(self, error_message: str) -> None:
        self.is_processing = False
        self.cancel_append_mode()
        self.clear_history_selection()
        for step_id, current in list(self.feedback_state.items()):
            if current == "active":
                self.feedback_state[step_id] = "error"
        self.latest_transcript = error_message
        self.raw_transcript = None
        self.latest_file_path = None
        retry_hint = "Press Space to try again." if self.input_source == "microphone" else "Press Enter on File to try again."
        self.set_status_message(f"Processing failed. {retry_hint}")
        self.refresh_feedback()
        self.refresh_transcript()
        self.refresh_status()

    def processing_finished(self, result: dict[str, str]) -> None:
        self.is_processing = False
        text = result.get("text", "") or "No transcript returned."
        prompt_id = result.get("prompt_id", "").strip()
        if self.append_mode:
            if self.append_base_text:
                text = self.append_base_text.rstrip() + "\n\n" + text
            target_id = self.append_target_id
            if target_id is not None and self.prompt_manager.update_prompt(target_id, text):
                prompt_id = str(target_id)
                self.selected_history_id = target_id
                self.selected_history_text = text
            self.cancel_append_mode()
        else:
            self.clear_history_selection()
        self.latest_transcript = text
        self.raw_transcript = result.get("raw_text") or self.raw_transcript
        self.latest_file_path = result.get("file_path")
        self.set_idle_status()
        self.refresh_transcript()
        self.refresh_status()
        self.refresh_history()
        if prompt_id:
            self.run_worker(lambda: self.generate_summary_for_prompt_worker(int(prompt_id), self.latest_transcript), thread=True, exclusive=False)

    def backfill_summaries_worker(self) -> None:
        if self.backfill_summaries is None:
            return
        self.call_from_thread(self.update_feedback_state, "summary", "active")
        try:
            updated = self.backfill_summaries()
        except Exception:
            self.call_from_thread(self.update_feedback_state, "summary", "error")
            return
        self.call_from_thread(self.update_feedback_state, "summary", "done")
        if updated:
            self.call_from_thread(self.refresh_history)

    def generate_summary_for_prompt_worker(self, prompt_id: int, prompt_text: str) -> None:
        if self.generate_summary is None:
            return
        self.call_from_thread(self.update_feedback_state, "summary", "active")
        try:
            summary = self.generate_summary(prompt_text, self.query_one("#llm_model", Input).value.strip() or self.default_llm_model)
        except Exception:
            self.call_from_thread(self.update_feedback_state, "summary", "error")
            return
        if not summary:
            self.call_from_thread(self.update_feedback_state, "summary", "pending")
            return
        updated = self.prompt_manager.update_prompt_summary(prompt_id, summary)
        if updated:
            self.call_from_thread(self.update_feedback_state, "summary", "done")
            self.call_from_thread(self.refresh_history)
        else:
            self.call_from_thread(self.update_feedback_state, "summary", "error")

    def action_save_transcript(self) -> None:
        text = self.get_editor_text().strip()
        if not text or text in {"No transcript yet.", "Recording in progress...", "Waiting for transcription..."}:
            self.set_status_message("No finished transcript to save yet.")
            self.refresh_status()
            return

        if self.selected_history_id is not None:
            saved = self.prompt_manager.update_prompt(self.selected_history_id, text)
            if saved:
                self.selected_history_text = text
                self.latest_transcript = text
                self.refresh_history()
                self.action_enter_command_mode()
                self.set_status_message(f"Saved transcription #{self.selected_history_id}.")
                self.refresh_status()
            else:
                self.set_status_message(f"Could not save transcription #{self.selected_history_id}.")
                self.refresh_status()
            return

        filename = self.latest_file_path or self.query_one("#file_path", Input).value.strip() or "manual-entry"
        prompt_id = self.prompt_manager.add_prompt(text, filename)
        if prompt_id is None:
            self.set_status_message("Could not save transcription.")
            self.refresh_status()
        else:
            self.selected_history_id = prompt_id
            self.selected_history_text = text
            self.selected_history_filename = filename
            self.latest_transcript = text
            self.refresh_history()
            self.action_enter_command_mode()
            self.set_status_message(f"Saved transcription #{prompt_id}.")
            self.refresh_status()

    def action_delete_selected_transcription(self) -> None:
        focused = self.focused
        if focused is None or focused.id != "history_list":
            return
        if self.selected_history_id is None:
            self.set_status_message("No transcription selected to delete.")
            self.refresh_status()
            return

        deleted_id = self.selected_history_id
        deleted = self.prompt_manager.remove_prompt_by_id(deleted_id)
        if deleted:
            self.latest_transcript = "No transcript yet."
            self.clear_history_selection()
            self.set_status_message(f"Deleted transcription #{deleted_id}.")
            self.refresh_history()
        else:
            self.set_status_message(f"Could not delete transcription #{deleted_id}.")
        self.refresh_status()

    def action_copy_transcript(self) -> None:
        text = self.get_editor_text().strip()
        if not text or text in {"No transcript yet.", "Recording in progress...", "Waiting for transcription..."}:
            self.set_status_message("No finished transcript to copy yet.")
        elif copy_text_to_clipboard(text):
            self.set_status_message("Copied transcript to clipboard.")
        else:
            self.set_status_message("Clipboard copy unavailable in this session.")
        self.refresh_status()

    def action_write_issue(self) -> None:
        if self.selected_history_id is None or self.selected_history_text is None:
            self.set_status_message("No transcription selected to write.")
            self.refresh_status()
            return

        summary = None
        for prompt in self.history_prompts:
            if prompt["id"] == self.selected_history_id:
                summary = str(prompt.get("summary") or "").strip()
                break

        issue_path = "/tmp/issue.md"
        file_existed = os.path.exists(issue_path)
        try:
            with open(issue_path, "w", encoding="utf-8") as f:
                if summary:
                    f.write(f"# {summary}\n\n")
                f.write(self.selected_history_text)
            if file_existed:
                self.set_status_message(f"{issue_path} was overwritten.")
            else:
                self.set_status_message(f"{issue_path} was written.")
        except OSError as e:
            self.set_status_message(f"Could not write {issue_path}: {e}")
        self.refresh_status()

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id == "history_list":
            self.select_history_prompt(event.option_index)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "history_list":
            self.select_history_prompt(event.option_index)

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "source_modes" and event.pressed.id:
            self.input_source = event.pressed.id.removeprefix("source-")
            self.persist_setting_value("input_source", self.input_source)
            self.set_idle_status()
            if self.input_source == "file":
                self.set_focus(self.query_one("#file_path", Input))
            self.refresh_status()
        elif event.radio_set.id == "preprocess_modes" and event.pressed.id:
            self.pre_process_mode = event.pressed.id.removeprefix("mode-")
            self.persist_setting_value("pre_process_mode", self.pre_process_mode)

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "file_path":
            self.persist_setting_value("file_path", event.value)
        elif event.input.id == "stt_model":
            value = event.value.strip()
            if value:
                self.persist_setting_value("stt_model", value)
        elif event.input.id == "llm_model":
            value = event.value.strip()
            if value:
                self.persist_setting_value("llm_model", value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "file_path":
            self.start_file_transcription()
