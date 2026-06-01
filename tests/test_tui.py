from __future__ import annotations

import pytest
from textual.widgets import Input, Label, ListView

from ds_cheatsheet.runner import RunResult
from ds_cheatsheet.tui.app import CheatSheetApp
from ds_cheatsheet.tui.run_result_screen import RunResultScreen
from ds_cheatsheet.tui.substitute_screen import SubstituteScreen


@pytest.mark.asyncio
async def test_theme_toggle_switches_between_dark_and_light() -> None:
    app = CheatSheetApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        assert app.theme == CheatSheetApp.DARK_THEME

        app.action_toggle_theme()
        await pilot.pause()
        assert app.theme == CheatSheetApp.LIGHT_THEME

        app.action_toggle_theme()
        await pilot.pause()
        assert app.theme == CheatSheetApp.DARK_THEME


@pytest.mark.asyncio
async def test_theme_keybinding_works_when_list_focused() -> None:
    app = CheatSheetApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#categories").focus()
        await pilot.pause()
        await pilot.press("t")
        await pilot.pause()
        assert app.theme == CheatSheetApp.LIGHT_THEME


@pytest.mark.asyncio
async def test_theme_keybinding_works_when_search_has_focus() -> None:
    app = CheatSheetApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        app.query_one("#search-input").focus()
        await pilot.pause()

        await pilot.press("t")
        await pilot.pause()

        assert app.theme == CheatSheetApp.LIGHT_THEME
        assert app.query_one("#search-input", Input).value == ""


@pytest.mark.asyncio
async def test_search_filters_commands() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#search-input").focus()
        await pilot.pause()
        for ch in "monitor gpu":
            await pilot.press(ch if ch != " " else "space")
        await pilot.pause()
        assert app.selected_id == "nvtop"


@pytest.mark.asyncio
async def test_down_from_search_focuses_commands_list() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#search-input", Input).focus()
        for ch in "monitor gpu":
            await pilot.press(ch if ch != " " else "space")
        await pilot.press("down")
        await pilot.pause()

        assert app.focused is app.query_one("#commands", ListView)


@pytest.mark.asyncio
async def test_enter_from_search_focuses_commands_and_keeps_first_match() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#search-input", Input).focus()
        for ch in "monitor gpu":
            await pilot.press(ch if ch != " " else "space")
        await pilot.press("enter")
        await pilot.pause()

        assert app.focused is app.query_one("#commands", ListView)
        assert app.selected_id == "nvtop"


@pytest.mark.asyncio
async def test_number_key_copies_specific_example(monkeypatch: pytest.MonkeyPatch) -> None:
    copied: list[str] = []
    monkeypatch.setattr(
        "ds_cheatsheet.tui.app.copy_to_clipboard",
        lambda text: copied.append(text) or (True, "Copied."),
    )

    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#commands", ListView).focus()
        app.selected_id = "tmux-new-session"
        app._refresh_detail()
        await pilot.press("1")
        await pilot.pause()

        assert copied == ["tmux new -s train"]
        assert app.status_message == "Copied example 1"


@pytest.mark.asyncio
async def test_missing_number_key_example_updates_status() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#commands", ListView).focus()
        app.selected_id = "tmux-new-session"
        app._refresh_detail()
        await pilot.press("9")
        await pilot.pause()

        assert app.status_message == "No example 9 for this entry."


@pytest.mark.asyncio
async def test_cycle_copy_target_walks_template_and_examples() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#commands", ListView).focus()
        app.selected_id = "tmux-new-session"
        app._refresh_detail()

        await pilot.press("C")
        await pilot.pause()
        assert app.copy_target_index == 0

        await pilot.press("C")
        await pilot.pause()
        assert app.copy_target_index == 1

        await pilot.press("C")
        await pilot.pause()
        assert app.copy_target_index == 2

        await pilot.press("C")
        await pilot.pause()
        assert app.copy_target_index == -1


@pytest.mark.asyncio
async def test_substitute_action_pushes_modal_for_placeholders() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#commands", ListView).focus()
        app.selected_id = "tmux-new-session"
        app._refresh_detail()

        await pilot.press("s")
        await pilot.pause()

        assert isinstance(app.screen, SubstituteScreen)


@pytest.mark.asyncio
async def test_substitute_callback_copies_filled_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    copied: list[str] = []
    monkeypatch.setattr(
        "ds_cheatsheet.tui.app.copy_to_clipboard",
        lambda text: copied.append(text) or (True, "Copied."),
    )

    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()

        app._copy_substituted_command("tmux new -s train")
        await pilot.pause()

        assert copied == ["tmux new -s train"]
        assert app.status_message == "Copied substituted command"


@pytest.mark.asyncio
async def test_category_list_shows_entry_counts() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()

        category_items = app.query_one("#categories", ListView).children
        labels = [str(item.query_one(Label).content) for item in category_items]

        assert "All (101)" in labels
        assert "gpu (5)" in labels


@pytest.mark.asyncio
async def test_recent_entries_are_prefixed_in_command_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ds_cheatsheet.tui.app.recent_entry_ids",
        lambda _repo_root: {"tmux-new-session"},
    )
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#search-input", Input).value = "tmux new session"
        await pilot.pause()

        first = app.query_one("#commands", ListView).children[0]
        label = first.query_one(Label)

        assert str(label.content).startswith("★ ")


@pytest.mark.asyncio
async def test_detail_panel_focus_and_scroll_keys_do_not_error() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.selected_id = "tmux-new-session"
        app._refresh_detail()

        await pilot.press("D")
        await pilot.press("pagedown")
        await pilot.press("pageup")
        await pilot.press("end")
        await pilot.press("home")
        await pilot.pause()

        assert app.focused is app.query_one("#detail")


@pytest.mark.asyncio
async def test_detail_search_opens_inline_input_and_tracks_matches() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.selected_id = "nvidia-smi"
        app._refresh_detail()

        await pilot.press("D")
        await pilot.press("slash")
        for ch in "GPU":
            await pilot.press(ch)
        await pilot.pause()

        detail_input = app.query_one("#detail-search-input", Input)
        assert app.focused is detail_input
        assert not detail_input.has_class("hidden")
        assert app.detail_search_query == "GPU"
        assert app.detail_search_match_count > 0


@pytest.mark.asyncio
async def test_explain_screen_lists_related_entries() -> None:
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()

        await pilot.press("E")
        await pilot.pause()
        for ch in "rg foo":
            await pilot.press(ch if ch != " " else "space")
        await pilot.press("enter")
        await pilot.pause()

        suggestions = app.screen.query_one("#explain-suggestions", ListView)
        suggestion_ids = [item.entry_id for item in suggestions.children]

        assert any(entry_id.startswith(("ripgrep", "grep")) for entry_id in suggestion_ids)


@pytest.mark.asyncio
async def test_run_command_opens_result_modal_without_replacing_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ds_cheatsheet.tui.app.run_command",
        lambda _command, confirm=True: RunResult("echo hi", True, 0, "hi\n", "", "ok"),
    )
    app = CheatSheetApp()
    async with app.run_test(size=(140, 40)) as pilot:
        await pilot.pause()
        app.query_one("#commands", ListView).focus()
        app.selected_id = "tmux-list-sessions"
        app._refresh_detail()
        detail_before = app.query_one("#detail-body").content

        await pilot.press("x")
        await pilot.pause()

        assert isinstance(app.screen, RunResultScreen)
        assert app.screen.result.stdout == "hi\n"
        assert app.query_one("#detail-body").content is detail_before
