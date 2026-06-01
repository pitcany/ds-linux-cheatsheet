from __future__ import annotations

from pathlib import Path

import pytest

from ds_cheatsheet.loader import (
    CheatSheetLoadError,
    categories,
    count_by_category,
    load_all,
    load_file,
)

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "commands"


def test_data_dir_exists() -> None:
    assert DATA_DIR.is_dir()
    yaml_files = list(DATA_DIR.glob("*.yaml"))
    assert yaml_files, "expected at least one YAML file"


def test_load_all_returns_entries() -> None:
    entries = load_all(DATA_DIR)
    assert len(entries) >= 100, f"expected >=100 commands, got {len(entries)}"


def test_every_entry_has_at_least_one_example() -> None:
    entries = load_all(DATA_DIR)
    missing = [e.id for e in entries if not e.examples]
    assert missing == [], f"entries without examples: {missing}"


def test_ids_are_unique() -> None:
    entries = load_all(DATA_DIR)
    ids = [e.id for e in entries]
    assert len(set(ids)) == len(ids)


def test_invalid_yaml_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("category: x\ncommands: not-a-list\n")
    with pytest.raises(CheatSheetLoadError):
        load_file(bad)


def test_categories_sorted() -> None:
    entries = load_all(DATA_DIR)
    cats = categories(entries)
    assert cats == sorted(cats)
    expected = {
        "tmux",
        "bash",
        "grep",
        "find",
        "awk",
        "sed",
        "xargs",
        "ssh",
        "git",
        "docker",
        "python_env",
        "jq",
        "csv_tools",
        "process",
        "disk",
        "gpu",
        "networking",
    }
    assert expected.issubset(set(cats))


def test_count_by_category_returns_entry_counts() -> None:
    entries = load_all(DATA_DIR)

    assert count_by_category(entries)["gpu"] == 5
