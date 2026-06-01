from __future__ import annotations

from pathlib import Path

import pyperclip

from ds_cheatsheet.clipboard import copy_to_clipboard


def test_copy_to_clipboard_writes_fallback_file_when_clipboard_fails(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    def fail_copy(_text: str) -> None:
        raise pyperclip.PyperclipException("no clipboard")

    monkeypatch.setattr(pyperclip, "copy", fail_copy)

    ok, message = copy_to_clipboard("echo hi")

    fallback = tmp_path / "ds-cheatsheet-last.txt"
    assert ok is False
    assert fallback.read_text(encoding="utf-8") == "echo hi"
    assert str(fallback) in message
