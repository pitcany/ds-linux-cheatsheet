"""Clipboard helper that fails gracefully on headless systems."""

from __future__ import annotations

import os
from pathlib import Path


def _fallback_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    base = Path(runtime_dir) if runtime_dir else Path("/tmp")
    return base / "ds-cheatsheet-last.txt"


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Attempt to copy text. Returns (success, message)."""
    try:
        import pyperclip  # local import — keeps startup cheap
    except ImportError:
        return False, "pyperclip is not installed."

    try:
        pyperclip.copy(text)
    except Exception as exc:  # pyperclip raises a custom exception family
        fallback = _fallback_path()
        try:
            fallback.write_text(text, encoding="utf-8")
        except OSError:
            return False, f"Clipboard unavailable: {exc}"
        return False, f"No clipboard — wrote {fallback} (press y to print to stdout)"
    return True, "Copied to clipboard."
