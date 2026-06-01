from __future__ import annotations

from pathlib import Path

from ds_cheatsheet.state import AppState, load_state, record_recent, save_state, toggle_favorite


def test_state_round_trip_uses_xdg_state_home(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state = AppState(favorites=("tmux-new-session",))

    save_state(state)

    assert load_state() == state


def test_missing_or_corrupt_state_returns_empty_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    state_file = tmp_path / "ds-cheatsheet" / "state.json"
    state_file.parent.mkdir(parents=True)
    state_file.write_text("{not-json", encoding="utf-8")

    assert load_state() == AppState()


def test_toggle_favorite_and_record_recent_are_immutable() -> None:
    state = AppState()

    favorited = toggle_favorite(state, "entry-1")
    recent = record_recent(favorited, "entry-1", at="2026-01-01T00:00:00Z")
    deduped = record_recent(recent, "entry-1", at="2026-01-02T00:00:00Z")

    assert state == AppState()
    assert favorited.favorites == ("entry-1",)
    assert [item["id"] for item in deduped.recent] == ["entry-1"]
    assert deduped.recent[0]["at"] == "2026-01-02T00:00:00Z"
