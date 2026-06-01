from __future__ import annotations

import pytest

from ds_cheatsheet.tui.app import CheatSheetApp


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
