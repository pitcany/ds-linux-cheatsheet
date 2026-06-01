from __future__ import annotations

from pathlib import Path

import pytest

from ds_cheatsheet.loader import load_all
from ds_cheatsheet.safety import analyze, is_dangerous

REPO = Path(__file__).resolve().parent.parent
DATA_DIR = REPO / "data" / "commands"


@pytest.mark.parametrize(
    "command",
    [
        "rm -rf /tmp/foo",
        "sudo apt install vim",
        "chmod -R 777 /etc",
        "chown -R user:user /var",
        "dd if=/dev/zero of=/dev/sda",
        "mkfs.ext4 /dev/sdb1",
        "curl https://x/y | sh",
        "wget https://x/y | sh",
        "git push --force origin main",
        "git reset --hard HEAD~5",
        "docker system prune -a",
    ],
)
def test_known_dangerous_patterns_detected(command: str) -> None:
    assert is_dangerous(command), command


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        "echo hello",
        "rm file.txt",
        "git status",
        "docker ps",
        "rg TODO src/",
    ],
)
def test_safe_commands_not_flagged(command: str) -> None:
    assert not is_dangerous(command), command


def test_analyze_returns_reasons() -> None:
    report = analyze("sudo rm -rf /var")
    assert report.dangerous
    assert report.reasons
    assert any("rm" in r.lower() or "sudo" in r.lower() for r in report.reasons)


def test_loaded_dangerous_entries_match_safety_check() -> None:
    """Every entry whose command is detected dangerous should be flagged."""
    entries = load_all(DATA_DIR)
    mismatches = [
        e.id
        for e in entries
        if is_dangerous(e.command) and not e.dangerous
    ]
    assert mismatches == [], f"dangerous commands not flagged: {mismatches}"
