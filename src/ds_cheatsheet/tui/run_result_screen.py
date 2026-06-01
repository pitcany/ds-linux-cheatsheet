"""Modal screen for command run results."""

from __future__ import annotations

from typing import ClassVar

from rich.panel import Panel
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from ..clipboard import copy_to_clipboard
from ..runner import RunResult


class RunResultScreen(ModalScreen[None]):
    """Show stdout, stderr, and return code for a command run."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "dismiss", "Close"),
        Binding("c", "copy_output", "Copy output"),
    ]

    DEFAULT_CSS = """
    RunResultScreen {
        align: center middle;
    }
    RunResultScreen > Vertical {
        width: 90;
        height: auto;
        max-height: 34;
        padding: 1 2;
        background: $boost;
        border: round $primary;
    }
    RunResultScreen Static {
        margin-bottom: 1;
    }
    """

    def __init__(self, result: RunResult, title: str) -> None:
        super().__init__()
        self.result = result
        self.result_title = title

    def compose(self) -> ComposeResult:
        stdout = self.result.stdout or "(no stdout)"
        stderr = self.result.stderr or "(no stderr)"
        yield Vertical(
            Label(f"{self.result_title}  |  exit {self.result.returncode}"),
            Static(Panel(Text(stdout[:4000]), title="stdout", border_style="green")),
            Static(Panel(Text(stderr[:4000]), title="stderr", border_style="red")),
            Button("Copy output", id="copy-output"),
            Label("", id="run-result-status"),
        )

    def action_copy_output(self) -> None:
        payload = self.result.stdout or self.result.stderr
        status = self.query_one("#run-result-status", Label)
        if not payload:
            status.update("No output to copy.")
            return
        ok, message = copy_to_clipboard(payload)
        status.update("Copied output." if ok else f"Copy failed: {message}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-output":
            self.action_copy_output()

    def action_dismiss(self, _result: None = None) -> None:
        self.dismiss(None)
