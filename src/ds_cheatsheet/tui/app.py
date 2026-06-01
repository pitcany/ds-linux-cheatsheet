"""Main Textual application."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import ClassVar

from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.widgets import Footer, Header, Input, Label, ListItem, ListView, Static

from ..clipboard import copy_to_clipboard
from ..explain import explain as explain_command
from ..git_meta import recent_entry_ids
from ..loader import CheatSheetLoadError, count_by_category, find_data_dir, load_all
from ..models import CommandEntry
from ..runner import run as run_command
from ..search import search as search_entries
from ..search import suggest as suggest_entries
from ..substitute import find_placeholders
from .help_screen import HelpScreen
from .substitute_screen import SubstituteScreen

_ALL_CATEGORIES = "All"


class CategoryItem(ListItem):
    """List entry that stores a category name."""

    def __init__(self, name: str, label: str | None = None) -> None:
        super().__init__(Label(label or name))
        self.category_name = name


class CommandItem(ListItem):
    """List entry that stores a CommandEntry id."""

    def __init__(self, entry: CommandEntry, *, is_recent: bool = False) -> None:
        title = entry.title
        if entry.dangerous or is_recent:
            parts: list[str | tuple[str, str]] = []
            if is_recent:
                parts.append(("★ ", "bold green"))
            if entry.dangerous:
                parts.append(("!! ", "bold red"))
            parts.append(title)
            label = Label(Text.assemble(*parts))
        else:
            label = Label(title)
        super().__init__(label)
        self.entry_id = entry.id


class SearchInput(Input):
    """Search box with app-level shortcuts that should win over typing."""

    def on_key(self, event: events.Key) -> None:
        if event.key == "t" and self.value == "":
            event.prevent_default()
            event.stop()
            self.app.action_toggle_theme()
        elif event.key == "D" and self.value == "":
            event.prevent_default()
            event.stop()
            self.app.action_focus_detail()
        elif event.key == "E" and self.value == "":
            event.prevent_default()
            event.stop()
            self.app.action_explain_prompt()
        elif event.key in {"down", "enter"}:
            event.prevent_default()
            event.stop()
            self.app.query_one("#commands", ListView).focus()


def _highlight_matches(text: str, query: str, *, style: str = "") -> Text:
    rendered = Text(text, style=style)
    if not query:
        return rendered
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    for match in pattern.finditer(text):
        rendered.stylize("reverse", match.start(), match.end())
    return rendered


def _render_detail(
    entry: CommandEntry | None,
    copy_target_index: int = -1,
    detail_search_query: str = "",
) -> Panel:
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

    command_style = "black on green" if copy_target_index == -1 else "white on grey15"
    table.add_row(
        "Command", _highlight_matches(entry.command, detail_search_query, style=command_style)
    )
    explanation = (
        _highlight_matches(entry.explanation, detail_search_query)
        if detail_search_query
        else Markdown(entry.explanation)
    )
    table.add_row("Explanation", explanation)

    if entry.flags:
        flags = Text("\n".join(f"  {f}" for f in entry.flags))
        table.add_row("Flags", flags)

    if entry.examples:
        ex_table = Table.grid(padding=(0, 1))
        ex_table.add_column()
        for idx, ex in enumerate(entry.examples):
            ex_block = Text()
            marker = f"[{idx + 1}] "
            if copy_target_index == idx:
                ex_block.append(marker, style="black on green")
            else:
                ex_block.append(marker, style="bold cyan")
            ex_block.append_text(
                _highlight_matches(f"{ex.description}\n", detail_search_query, style="italic")
            )
            command_style = "black on green" if copy_target_index == idx else "white on grey15"
            ex_block.append_text(
                _highlight_matches(f"    $ {ex.command}", detail_search_query, style=command_style)
            )
            ex_table.add_row(ex_block)
        table.add_row("Examples", ex_table)

    if entry.gotchas:
        gotchas = Text("\n".join(f"  • {g}" for g in entry.gotchas), style="yellow")
        table.add_row("Gotchas", gotchas)

    if entry.tags:
        table.add_row("Tags", Text(" ".join(f"#{t}" for t in entry.tags), style="cyan"))

    if entry.dangerous:
        table.add_row(
            "Safety", Text("Marked dangerous — runner requires confirm+force.", style="red")
        )

    if detail_search_query:
        table.add_row("Find", _highlight_matches(detail_search_query, detail_search_query))

    return Panel(table, title=title, border_style="magenta")


class CheatSheetApp(App[None]):
    """Textual application — three-pane cheat sheet browser."""

    CSS_PATH = "styles.tcss"
    TITLE = "ds-linux-cheatsheet"
    SUB_TITLE = "Linux commands for data scientists"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("?", "show_help", "Help"),
        Binding("slash", "focus_search", "Search"),
        Binding("c", "copy_command", "Copy"),
        Binding("C", "cycle_copy_target", "Cycle"),
        Binding("s", "substitute_command", "Substitute"),
        Binding("D", "focus_detail", "Detail"),
        Binding("pagedown", "detail_page_down", "Page down", show=False),
        Binding("pageup", "detail_page_up", "Page up", show=False),
        Binding("home", "detail_home", "Top", show=False),
        Binding("end", "detail_end", "Bottom", show=False),
        Binding("n", "next_detail_match", "Next match", show=False),
        Binding("N", "previous_detail_match", "Previous match", show=False),
        Binding("e", "edit_yaml", "Edit YAML"),
        Binding("x", "run_command", "Run"),
        Binding("E", "explain_prompt", "Explain"),
        Binding("t", "toggle_theme", "Theme", priority=True),
        Binding("1", "copy_example(1)", "Example 1", show=False),
        Binding("2", "copy_example(2)", "Example 2", show=False),
        Binding("3", "copy_example(3)", "Example 3", show=False),
        Binding("4", "copy_example(4)", "Example 4", show=False),
        Binding("5", "copy_example(5)", "Example 5", show=False),
        Binding("6", "copy_example(6)", "Example 6", show=False),
        Binding("7", "copy_example(7)", "Example 7", show=False),
        Binding("8", "copy_example(8)", "Example 8", show=False),
        Binding("9", "copy_example(9)", "Example 9", show=False),
        Binding("j", "move_down", "Down"),
        Binding("k", "move_up", "Up"),
        Binding("tab", "cycle_focus", "Cycle"),
    ]

    DARK_THEME = "textual-dark"
    LIGHT_THEME = "textual-light"

    query: reactive[str] = reactive("")
    current_category: reactive[str] = reactive(_ALL_CATEGORIES)
    selected_id: reactive[str | None] = reactive(None)
    copy_target_index: reactive[int] = reactive(-1)

    def __init__(self) -> None:
        super().__init__()
        self.entries: list[CommandEntry] = []
        self.entries_by_id: dict[str, CommandEntry] = {}
        self.data_dir: Path | None = None
        self.status_message: str = ""
        self.category_counts: dict[str, int] = {}
        self.recent_ids: set[str] = set()
        self.detail_search_query: str = ""
        self.detail_search_match_count: int = 0
        self.detail_search_match_index: int = 0

    # ------------------------------------------------------------------ compose

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="top-bar"):
            yield SearchInput(placeholder="Search…  (press / to focus)", id="search-input")
            yield Label("", id="status")
        with Horizontal(id="main"):
            yield ListView(id="categories")
            yield ListView(id="commands")
            with VerticalScroll(id="detail", can_focus=True):
                yield Static(_render_detail(None, -1), id="detail-body")
                yield Input(placeholder="Find in entry", id="detail-search-input", classes="hidden")
        yield Footer()

    # ------------------------------------------------------------------ lifecycle

    def on_mount(self) -> None:
        try:
            self.entries = load_all()
            self.data_dir = find_data_dir()
            self.recent_ids = recent_entry_ids(self.data_dir.parent.parent)
        except CheatSheetLoadError as exc:
            self.entries = []
            self._set_status(f"Load error: {exc}")

        self.entries_by_id = {e.id: e for e in self.entries}
        self.category_counts = count_by_category(self.entries)
        self._refresh_categories()
        self._refresh_commands()

    # ------------------------------------------------------------------ helpers

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.query_one("#status", Label).update(message)

    def _current_entry(self) -> CommandEntry | None:
        return self.entries_by_id.get(self.selected_id) if self.selected_id else None

    def _resolve_copy_target(self, entry: CommandEntry) -> tuple[str, str]:
        if self.copy_target_index == -1:
            return entry.command, "template"
        if 0 <= self.copy_target_index < len(entry.examples):
            return entry.examples[
                self.copy_target_index
            ].command, f"example {self.copy_target_index + 1}"
        return entry.command, "template"

    def _refresh_categories(self) -> None:
        view = self.query_one("#categories", ListView)
        view.clear()
        view.append(CategoryItem(_ALL_CATEGORIES, f"{_ALL_CATEGORIES} ({len(self.entries)})"))
        cats = sorted({e.category for e in self.entries})
        for cat in cats:
            view.append(CategoryItem(cat, f"{cat} ({self.category_counts.get(cat, 0)})"))
        view.index = 0

    def _refresh_commands(self) -> None:
        view = self.query_one("#commands", ListView)
        view.clear()
        category = None if self.current_category == _ALL_CATEGORIES else self.current_category
        results = search_entries(self.entries, self.query, category=category)
        for entry in results:
            view.append(CommandItem(entry, is_recent=entry.id in self.recent_ids))
        if results:
            view.index = 0
            self.selected_id = results[0].id
            self._refresh_detail()
            self._set_status(f"{len(results)} matches")
        else:
            self.selected_id = None
            self._refresh_detail()
            suggestions = suggest_entries(self.entries, self.query)
            if suggestions:
                self._set_status(f"No matches. Did you mean: {', '.join(suggestions)}")
            else:
                self._set_status("No matches")

    def _refresh_detail(self) -> None:
        entry = self._current_entry()
        self.detail_search_match_count = self._count_detail_matches(entry, self.detail_search_query)
        self.query_one("#detail-body", Static).update(
            _render_detail(entry, self.copy_target_index, self.detail_search_query)
        )

    def _count_detail_matches(self, entry: CommandEntry | None, query: str) -> int:
        if entry is None or not query:
            return 0
        haystack = "\n".join(
            [
                entry.command,
                entry.explanation,
                "\n".join(example.description for example in entry.examples),
                "\n".join(example.command for example in entry.examples),
            ]
        )
        return len(re.findall(re.escape(query), haystack, flags=re.IGNORECASE))

    def watch_selected_id(self, old: str | None, new: str | None) -> None:
        if old != new:
            self.copy_target_index = -1

    # ------------------------------------------------------------------ events

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id == "search-input":
            self.query = event.value
            self._refresh_commands()
        elif event.input.id == "detail-search-input":
            self.detail_search_query = event.value
            self.detail_search_match_index = 0
            self._refresh_detail()

    def on_key(self, event: events.Key) -> None:
        if self.focused is not None and self.focused.id == "search-input":
            if event.key == "t" and self.query_one("#search-input", Input).value == "":
                event.prevent_default()
                event.stop()
                self.action_toggle_theme()
                return
            if event.key == "D" and self.query_one("#search-input", Input).value == "":
                event.prevent_default()
                event.stop()
                self.action_focus_detail()
                return
            if event.key == "E" and self.query_one("#search-input", Input).value == "":
                event.prevent_default()
                event.stop()
                self.action_explain_prompt()
                return
            if event.key in {"down", "enter"}:
                event.prevent_default()
                event.stop()
                self.query_one("#commands", ListView).focus()
        elif self.focused is not None and self.focused.id == "detail-search-input":
            if event.key == "escape":
                event.prevent_default()
                event.stop()
                self._close_detail_search()

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
        if self.focused is self.query_one("#detail", VerticalScroll):
            self._open_detail_search()
            return
        self.query_one("#search-input", Input).focus()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_toggle_theme(self) -> None:
        self.theme = self.LIGHT_THEME if self.theme == self.DARK_THEME else self.DARK_THEME
        self._set_status(f"Theme: {self.theme}")

    def action_copy_command(self) -> None:
        entry = self._current_entry()
        if entry is None:
            self._set_status("Nothing to copy.")
            return
        command, label = self._resolve_copy_target(entry)
        ok, msg = copy_to_clipboard(command)
        self._set_status(f"Copied {label}" if ok else f"Copy failed: {msg}")

    def action_copy_example(self, number: int) -> None:
        entry = self._current_entry()
        if entry is None:
            self._set_status("Nothing to copy.")
            return
        index = number - 1
        if index < 0 or index >= len(entry.examples):
            self._set_status(f"No example {number} for this entry.")
            return
        self.copy_target_index = index
        self._refresh_detail()
        self.action_copy_command()

    def action_cycle_copy_target(self) -> None:
        entry = self._current_entry()
        if entry is None:
            self._set_status("Nothing to copy.")
            return
        next_index = self.copy_target_index + 1
        self.copy_target_index = -1 if next_index >= len(entry.examples) else next_index
        self._refresh_detail()
        if self.copy_target_index == -1:
            self._set_status("Copy target: template")
        else:
            self._set_status(f"Copy target: example {self.copy_target_index + 1}")

    def action_substitute_command(self) -> None:
        entry = self._current_entry()
        if entry is None:
            self._set_status("Nothing to substitute.")
            return
        command, _label = self._resolve_copy_target(entry)
        placeholders = find_placeholders(command)
        if not placeholders:
            ok, msg = copy_to_clipboard(command)
            self._set_status("No placeholders to fill." if ok else f"Copy failed: {msg}")
            return
        self.push_screen(
            SubstituteScreen(command, placeholders),
            self._copy_substituted_command,
        )

    def _copy_substituted_command(self, command: str | None) -> None:
        if command is None:
            self._set_status("Substitution cancelled.")
            return
        ok, msg = copy_to_clipboard(command)
        self._set_status("Copied substituted command" if ok else f"Copy failed: {msg}")

    def action_edit_yaml(self) -> None:
        entry = self._current_entry()
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
            self.category_counts = count_by_category(self.entries)
            self._refresh_categories()
            self._refresh_commands()
            self._set_status(f"Reloaded {len(self.entries)} commands.")
        except CheatSheetLoadError as exc:
            self._set_status(f"Reload error: {exc}")

    def action_run_command(self) -> None:
        entry = self._current_entry()
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
        order = ["#search-input", "#categories", "#commands", "#detail"]
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

    def action_focus_detail(self) -> None:
        self.query_one("#detail", VerticalScroll).focus()

    def _open_detail_search(self) -> None:
        search_input = self.query_one("#detail-search-input", Input)
        search_input.remove_class("hidden")
        search_input.focus()

    def _close_detail_search(self) -> None:
        search_input = self.query_one("#detail-search-input", Input)
        search_input.value = ""
        search_input.add_class("hidden")
        self.detail_search_query = ""
        self.detail_search_match_count = 0
        self.detail_search_match_index = 0
        self._refresh_detail()
        self.action_focus_detail()

    def action_detail_page_down(self) -> None:
        if self.focused is self.query_one("#detail", VerticalScroll):
            self.query_one("#detail", VerticalScroll).scroll_page_down()

    def action_detail_page_up(self) -> None:
        if self.focused is self.query_one("#detail", VerticalScroll):
            self.query_one("#detail", VerticalScroll).scroll_page_up()

    def action_detail_home(self) -> None:
        if self.focused is self.query_one("#detail", VerticalScroll):
            self.query_one("#detail", VerticalScroll).scroll_home()

    def action_detail_end(self) -> None:
        if self.focused is self.query_one("#detail", VerticalScroll):
            self.query_one("#detail", VerticalScroll).scroll_end()

    def action_next_detail_match(self) -> None:
        if self.detail_search_match_count:
            self.detail_search_match_index = (
                self.detail_search_match_index + 1
            ) % self.detail_search_match_count
            self._set_status(
                f"Detail match {self.detail_search_match_index + 1}/{self.detail_search_match_count}"
            )

    def action_previous_detail_match(self) -> None:
        if self.detail_search_match_count:
            self.detail_search_match_index = (
                self.detail_search_match_index - 1
            ) % self.detail_search_match_count
            self._set_status(
                f"Detail match {self.detail_search_match_index + 1}/{self.detail_search_match_count}"
            )

    def _move_focused_list(self, delta: int) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            if focused.index is None:
                focused.index = 0
            else:
                focused.index = max(0, min(len(focused) - 1, focused.index + delta))

    def jump_to_entry(self, entry_id: str) -> None:
        entry = self.entries_by_id.get(entry_id)
        if entry is None:
            self._set_status(f"Entry {entry_id} not found.")
            return

        self.current_category = entry.category
        self.query = ""
        self.query_one("#search-input", Input).value = ""
        self._refresh_categories()
        self._refresh_commands()
        commands = self.query_one("#commands", ListView)
        for index, item in enumerate(commands.children):
            if isinstance(item, CommandItem) and item.entry_id == entry_id:
                commands.index = index
                break
        self.selected_id = entry_id
        self._refresh_detail()
        commands.focus()
        self._set_status(f"Jumped to {entry.title}")


class _ExplainSuggestionItem(ListItem):
    """List entry that stores a related command id."""

    def __init__(self, entry: CommandEntry) -> None:
        super().__init__(Label(entry.title))
        self.entry_id = entry.id


class _ExplainScreen(HelpScreen):  # reuse modal styling
    """Modal that asks for a command and displays its explanation."""

    BINDINGS: ClassVar[list[Binding]] = [Binding("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("Paste a command to explain — press enter:")
            yield Input(placeholder="e.g. rg -uu --hidden TODO ./src", id="explain-input")
            yield Static("", id="explain-output")
            yield ListView(id="explain-suggestions")

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
        self._refresh_suggestions(event.value)

    def _refresh_suggestions(self, command: str) -> None:
        suggestions = self.query_one("#explain-suggestions", ListView)
        suggestions.clear()
        first_token = command.strip().split(maxsplit=1)[0] if command.strip() else ""
        if not first_token:
            return
        app = self.app
        if not isinstance(app, CheatSheetApp):
            return
        results = search_entries(app.entries, first_token)
        results.sort(
            key=lambda entry: (
                0 if entry.command.strip().split(maxsplit=1)[0] == first_token else 1,
                entry.title.lower(),
            )
        )
        for entry in results[:3]:
            suggestions.append(_ExplainSuggestionItem(entry))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, _ExplainSuggestionItem):
            return
        app = self.app
        if isinstance(app, CheatSheetApp):
            self.dismiss(None)
            app.call_after_refresh(app.jump_to_entry, item.entry_id)
