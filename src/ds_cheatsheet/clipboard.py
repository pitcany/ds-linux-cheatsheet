"""Clipboard helper that fails gracefully on headless systems."""

from __future__ import annotations


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Attempt to copy text. Returns (success, message)."""
    try:
        import pyperclip  # local import — keeps startup cheap
    except ImportError:
        return False, "pyperclip is not installed."

    try:
        pyperclip.copy(text)
    except Exception as exc:  # pyperclip raises a custom exception family
        return False, f"Clipboard unavailable: {exc}"
    return True, "Copied to clipboard."
