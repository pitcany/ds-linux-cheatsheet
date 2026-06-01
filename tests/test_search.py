from __future__ import annotations

from pathlib import Path

from ds_cheatsheet.loader import load_all
from ds_cheatsheet.search import search

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "commands"


def _entries() -> list:
    return load_all(DATA_DIR)


def test_empty_query_returns_all_sorted() -> None:
    entries = _entries()
    results = search(entries, "")
    assert len(results) == len(entries)


def test_intent_find_large_files() -> None:
    entries = _entries()
    results = search(entries, "find large files")
    ids = [e.id for e in results]
    assert "find-large-files" in ids


def test_intent_search_logs() -> None:
    entries = _entries()
    results = search(entries, "search logs")
    cats = {e.category for e in results}
    assert {"grep", "process"} & cats


def test_intent_monitor_gpu() -> None:
    entries = _entries()
    results = search(entries, "monitor gpu")
    assert any(e.category == "gpu" for e in results)


def test_intent_kill_process() -> None:
    entries = _entries()
    results = search(entries, "kill process")
    assert any("kill" in e.id for e in results)


def test_intent_tmux_new_session() -> None:
    entries = _entries()
    results = search(entries, "tmux new session")
    assert results
    assert results[0].category == "tmux"


def test_intent_copy_files_to_server() -> None:
    entries = _entries()
    results = search(entries, "copy files to server")
    ids = {e.id for e in results}
    assert {"scp-basic", "rsync-sync"} & ids


def test_intent_split_csv() -> None:
    entries = _entries()
    results = search(entries, "split csv")
    assert any(e.id == "split-csv-rows" for e in results)


def test_category_filter() -> None:
    entries = _entries()
    results = search(entries, "", category="git")
    assert results
    assert all(e.category == "git" for e in results)


def test_unknown_query_returns_empty() -> None:
    entries = _entries()
    results = search(entries, "asdfqwerasdf-no-such-token")
    assert results == []
