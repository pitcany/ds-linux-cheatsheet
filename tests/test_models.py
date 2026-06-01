from __future__ import annotations

import pytest
from pydantic import ValidationError

from ds_cheatsheet.models import CommandEntry, Example


def test_minimal_entry_validates() -> None:
    entry = CommandEntry(
        id="x",
        title="X",
        category="cat",
        command="echo hi",
        explanation="prints",
    )
    assert entry.id == "x"
    assert entry.examples == []
    assert entry.dangerous is False


def test_blank_strings_rejected() -> None:
    with pytest.raises(ValidationError):
        CommandEntry(id="", title="t", category="c", command="x", explanation="y")


def test_tags_stripped() -> None:
    entry = CommandEntry(
        id="x",
        title="t",
        category="c",
        command="x",
        explanation="y",
        tags=["  one ", "", "two"],
    )
    assert entry.tags == ["one", "two"]


def test_search_text_combines_fields() -> None:
    entry = CommandEntry(
        id="x",
        title="Hello World",
        category="bash",
        command="echo hi",
        explanation="prints a greeting",
        tags=["greeting"],
        examples=[Example(description="greet", command="echo hello")],
    )
    haystack = entry.search_text
    assert "hello world" in haystack
    assert "greet" in haystack
    assert "echo hello" in haystack
    assert "greeting" in haystack
