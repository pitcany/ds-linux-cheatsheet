from __future__ import annotations

from ds_cheatsheet.substitute import find_placeholders, substitute


def test_find_placeholders_returns_deduped_names_in_first_seen_order() -> None:
    command = "rsync -avzP <src>/ <user>@<host>:<dst>/ <src>"

    assert find_placeholders(command) == ["src", "user", "host", "dst"]


def test_substitute_replaces_known_placeholders_and_leaves_missing_tokens() -> None:
    command = "scp <src> <host>:<dst>"

    assert substitute(command, {"src": "a", "dst": "/b"}) == "scp a <host>:/b"
