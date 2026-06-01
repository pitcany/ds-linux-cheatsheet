from __future__ import annotations

from pathlib import Path

from ds_cheatsheet.tui.app import editor_command


def test_editor_command_for_vim_like_editors() -> None:
    path = Path("/tmp/foo.yaml")

    assert editor_command("vi", path, 12) == ["vi", "+12", "/tmp/foo.yaml"]
    assert editor_command("nvim", path, 12) == ["nvim", "+12", "/tmp/foo.yaml"]


def test_editor_command_for_code_like_editors() -> None:
    path = Path("/tmp/foo.yaml")

    assert editor_command("code", path, 12) == ["code", "--goto", "/tmp/foo.yaml:12"]
    assert editor_command("codium", path, 12) == ["codium", "--goto", "/tmp/foo.yaml:12"]


def test_editor_command_for_nano_and_unknown_editors() -> None:
    path = Path("/tmp/foo.yaml")

    assert editor_command("nano", path, 12) == ["nano", "+12", "/tmp/foo.yaml"]
    assert editor_command("foo", path, 12) == ["foo", "/tmp/foo.yaml"]
