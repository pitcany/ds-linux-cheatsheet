"""Help modal screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

HELP_TEXT = """[b]ds-linux-cheatsheet[/b]

[b]Navigation[/b]
  /            focus the search box
  j / k        move down / up in the current list
  arrows       same as j / k
  tab          cycle between panels
  enter        open the selected command

[b]Actions[/b]
  c            copy the selected command to the clipboard
  e            edit the underlying YAML file in $EDITOR
  x            run the selected command (with safety prompt)
  E            explain a command you type
  ?            this help screen
  q            quit

[b]Safety[/b]
  Commands flagged [red]!! dangerous[/red] require an explicit second
  confirmation before being executed. Default mode is copy-only.

Press [b]escape[/b] to dismiss.
"""


class HelpScreen(ModalScreen[None]):
    """Modal that prints keyboard shortcuts and safety notes."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    HelpScreen > Vertical {
        width: 70;
        height: auto;
        padding: 1 2;
        background: $boost;
        border: round $primary;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(HELP_TEXT, markup=True)

    def action_dismiss(self, _result: None = None) -> None:
        self.dismiss(None)
