"""Main Textual application."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from ..clipboard import copy_to_clipboard
from ..explain import explain as explain_command
from ..loader import CheatSheetLoadError, find_data_dir, load_all
from ..models import CommandEntry
from ..runner import run as run_command
from ..search import search as search_entries
from .help_screen import HelpScreen


_ALL_CATEGORIES = "All"


class CategoryItem(ListItem):
    """List entry that stores a category name."""

    def __init__(self, name: str) -> None:
        super().__init__(Label(name))
        self.category_name = name


class CommandItem(ListItem):
    """List entry that stores a CommandEntry id."""

    def __init__(self, entry: CommandEntry) -> None:
        title = entry.title
        if entry.dangerous:
            label = Label(Text.assemble(("!! ", "bold red"), title))
        else:
            label = Label(title)
        super().__init__(label)
        self.entry_id = entry.id


def _render_detail(entry: CommandEntry | None) -> Panel:
    """Render the detail panel for a selected command."""
    if entry is None:
        return Panel(Text("Select a command to see details.", style="dim"), title="Detail")

    title = Text()
    if entry.dangerous:
        title.append("!! ", style="bold red")
    title.append(entry.title, style="bold")
    title.append(f"  [{entry.category}]", style="dim")

    table = Table.grid(padding=(0, 1))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column()

    table.add_row("Command", Text(entry.command, style="white on grey15"))
    table.add_row("Explanation", Markdown(entry.explanation))

    if entry.flags:
        flags = Text("\n".join(f"  {f}" for f in entry.flags))
        table.add_row("Flags", flags)

    if entry.examples:
        ex_table = Table.grid(padding=(0, 1))
        ex_table.add_column()
        for idx, ex in enumerate(entry.examples, start=1):
            ex_block = Text()
            ex_block.append(f"{idx}. {ex.description}\n", style="italic")
            ex_block.append(f"   $ {ex.command}", style="white on grey15")
            ex_table.add_row(ex_block)
        table.add_row("Examples", ex_table)

    if entry.gotchas:
        gotchas = Text("\n".join(f"  • {g}" for g in entry.gotchas), style="yellow")
        table.add_row("Gotchas", gotchas)

    if entry.tags:
        table.add_row("Tags", Text(" ".join(f"#{t}" for t in entry.tags), style="cyan"))

    if entry.dangerous:
        table.add_row("Safety", Text("Marked dangerous — runner requires confirm+force.", style="red"))

    return Panel(table, title=title, border_style="magenta")


class CheatSheetApp(App[None]):
    """Textual application — three-pane cheat sheet browser."""

    CSS_PATH = "styles.tcss"
    TITLE = "ds-linux-cheatsheet"
    SUB_TITLE = "Linux commands for data scientists"

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("?", "show_help", "Help"),
        Binding("slash", "focus_search", "Search"),
        Binding("c", "copy_command", "Copy"),
        Binding("e", "edit_yaml", "Edit YAML"),
        Binding("x", "run_command", "Run"),
        Binding("E", "explain_prompt", "Explain"),
        Binding("t", "toggle_theme", "Theme"),
        Binding("j", "move_down", show=False),
        Binding("k", "move_up", show=False),
        Binding("tab", "cycle_focus", show=False),
    ]

    DARK_THEME = "textual-dark"
    LIGHT_THEME = "textual-light"

    query: reactive[str] = reactive("")
    current_category: reactive[str] = reactive(_ALL_CATEGORIES)
    selected_id: reactive[str | None] = reactive(None)

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[CommandEntry] = []
        self.entries_by_id: dict[str, CommandEntry] = {}
        self.data_dir: Path | None = None
        self.status_message: str = ""

    # ------------------------------------------------------------------ compose

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="top-bar"):
            yield Input(placeholder="Search…  (press / to focus)", id="search-input")
            yield Label("", id="status")
        with Horizontal(id="main"):
            yield ListView(id="categories")
            yield ListView(id="commands")
            with VerticalScroll(id="detail"):
                yield Static(_render_detail(None), id="detail-body")
        yield Footer()

    # ------------------------------------------------------------------ lifecycle

    def on_mount(self) -> None:
        try:
            self.entries = load_all()
            self.data_dir = find_data_dir()
        except CheatSheetLoadError as exc:
            self.entries = []
            self._set_status(f"Load error: {exc}")

        self.entries_by_id = {e.id: e for e in self.entries}
        self._refresh_categories()
        self._refresh_commands()

    # ------------------------------------------------------------------ helpers

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.query_one("#status", Label).update(message)

    def _refresh_categories(self) -> None:
        view = self.query_one("#categories", ListView)
        view.clear()
        view.append(CategoryItem(_ALL_CATEGORIES))
        cats = sorted({e.category for e in self.entries})
        for cat in cats:
            view.append(CategoryItem(cat))
        view.index = 0

    def _refresh_commands(self) -> None:
        view = self.query_one("#commands", ListView)
        view.clear()
        category = None if self.current_category == _ALL_CATEGORIES else self.current_category
        results = search_entries(self.entries, self.query, category=category)
        for entry in results:
            view.append(CommandItem(entry))
        if results:
            view.index = 0
            self.selected_id = results[0].id
            self._refresh_detail()
            self._set_status(f"{len(results)} matches")
        else:
            self.selected_id = None
            self._refresh_detail()
            self._set_status("No matches")

    def _refresh_detail(self) -> None:
        entry = self.entries_by_id.get(self.selected_id) if self.selected_id else None
        self.query_one("#detail-body", Static).update(_render_detail(entry))

    # ------------------------------------------------------------------ events

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query = event.value
            self._refresh_commands()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if isinstance(item, CategoryItem):
            self.current_category = item.category_name
            self._refresh_commands()
        elif isinstance(item, CommandItem):
            self.selected_id = item.entry_id
            self._refresh_detail()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        item = event.item
        if isinstance(item, CategoryItem):
            self.current_category = item.category_name
            self._refresh_commands()
        elif isinstance(item, CommandItem):
            self.selected_id = item.entry_id
            self._refresh_detail()

    # ------------------------------------------------------------------ actions

    def action_focus_search(self) -> None:
        self.query_one("#search-input", Input).focus()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_theme(self) -> None:
        self.theme = self.LIGHT_THEME if self.theme == self.DARK_THEME else self.DARK_THEME
        self._set_status(f"Theme: {self.theme}")

    def action_copy_command(self) -> None:
        entry = self.entries_by_id.get(self.selected_id) if self.selected_id else None
        if entry is None:
            self._set_status("Nothing to copy.")
            return
        ok, msg = copy_to_clipboard(entry.command)
        self._set_status(msg if ok else f"Copy failed: {msg}")

    def action_edit_yaml(self) -> None:
        entry = self.entries_by_id.get(self.selected_id) if self.selected_id else None
        if entry is None or self.data_dir is None:
            self._set_status("Nothing to edit.")
            return

        editor = os.environ.get("EDITOR", "vi")
        # Heuristic: find the YAML file that mentions this entry id.
        target: Path | None = None
        for yaml_path in sorted(self.data_dir.glob("*.yaml")):
            try:
                if f"id: {entry.id}" in yaml_path.read_text(encoding="utf-8"):
                    target = yaml_path
                    break
            except OSError:
                continue

        if target is None:
            self._set_status(f"YAML file for {entry.id} not found.")
            return

        with self.suspend():
            subprocess.call([editor, str(target)])

        try:
            self.entries = load_all()
            self.entries_by_id = {e.id: e for e in self.entries}
            self._refresh_categories()
            self._refresh_commands()
            self._set_status(f"Reloaded {len(self.entries)} commands.")
        except CheatSheetLoadError as exc:
            self._set_status(f"Reload error: {exc}")

    def action_run_command(self) -> None:
        entry = self.entries_by_id.get(self.selected_id) if self.selected_id else None
        if entry is None:
            self._set_status("Nothing to run.")
            return

        if entry.dangerous:
            result = run_command(entry.command, confirm=True, force=False)
            self._set_status(result.reason)
            return

        result = run_command(entry.command, confirm=True)
        if result.executed:
            self._set_status(f"Exit {result.returncode} — see detail panel.")
            preview = (result.stdout or result.stderr or "(no output)")[:1500]
            body = Panel(
                Text(preview),
                title=f"Run result: {entry.title}",
                border_style="green" if result.returncode == 0 else "red",
            )
            self.query_one("#detail-body", Static).update(body)
        else:
            self._set_status(result.reason)

    def action_explain_prompt(self) -> None:
        """Push a small inline modal to explain a typed command."""
        self.push_screen(_ExplainScreen())

    def action_move_down(self) -> None:
        self._move_focused_list(1)

    def action_move_up(self) -> None:
        self._move_focused_list(-1)

    def action_cycle_focus(self) -> None:
        order = ["#search-input", "#categories", "#commands"]
        focused = self.focused
        if focused is None:
            self.query_one(order[0]).focus()
            return
        for i, sel in enumerate(order):
            if focused.id and focused.id == sel.lstrip("#"):
                next_sel = order[(i + 1) % len(order)]
                self.query_one(next_sel).focus()
                return
        self.query_one(order[0]).focus()

    def _move_focused_list(self, delta: int) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            if focused.index is None:
                focused.index = 0
            else:
                focused.index = max(0, min(len(focused) - 1, focused.index + delta))


class _ExplainScreen(HelpScreen):  # reuse modal styling
    """Modal that asks for a command and displays its explanation."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Paste a command to explain — press enter:")
            yield Input(placeholder="e.g. rg -uu --hidden TODO ./src", id="explain-input")
            yield Static("", id="explain-output")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id != "explain-input":
            return
        ex = explain_command(event.value)
        lines: list[str] = [f"[b]Command:[/b] {ex.command}", ""]
        for token in ex.tokens:
            lines.append(f"  [{token.kind}] [b]{token.value}[/b] — {token.description}")
        if ex.dangerous:
            lines.append("")
            lines.append("[red]!! Dangerous patterns detected:[/red]")
            for reason in ex.danger_reasons:
                lines.append(f"  - {reason}")
        self.query_one("#explain-output", Static).update("\n".join(lines))
