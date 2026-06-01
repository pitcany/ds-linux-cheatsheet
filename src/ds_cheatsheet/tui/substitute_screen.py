"""Modal screen for filling command placeholders."""

from __future__ import annotations

from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label

from ..substitute import substitute


class SubstituteScreen(ModalScreen[str | None]):
    """Collect placeholder values and return a substituted command."""

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("escape", "cancel", "Cancel"),
        Binding("enter", "submit", "Copy"),
    ]

    DEFAULT_CSS = """
    SubstituteScreen {
        align: center middle;
    }
    SubstituteScreen > Vertical {
        width: 72;
        height: auto;
        padding: 1 2;
        background: $boost;
        border: round $primary;
    }
    SubstituteScreen Input {
        margin-bottom: 1;
    }
    """

    def __init__(self, command: str, placeholders: list[str]) -> None:
        super().__init__()
        self.command = command
        self.placeholders = placeholders

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Fill placeholders, then press enter.")
            for placeholder in self.placeholders:
                yield Label(f"<{placeholder}>")
                yield Input(placeholder=placeholder, id=f"placeholder-{placeholder}")

    def action_submit(self) -> None:
        values: dict[str, str] = {}
        for placeholder in self.placeholders:
            value = self.query_one(f"#placeholder-{placeholder}", Input).value
            if value:
                values = {**values, placeholder: value}
        self.dismiss(substitute(self.command, values))

    def action_cancel(self) -> None:
        self.dismiss(None)
