"""Read optional git metadata for cheat sheet entries."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ENTRY_ID_RE = re.compile(r"^\+\s*-?\s*id:\s*([A-Za-z0-9_.-]+)\s*$")


def recent_entry_ids(repo_root: Path, days: int = 7) -> set[str]:
    """Return ids whose YAML entry line was added in recent git history."""
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                f"--since={days} days ago",
                "--unified=0",
                "--no-ext-diff",
                "--",
                "data/commands/*.yaml",
            ],
            check=False,
            capture_output=True,
            text=True,
        )
    except (OSError, ValueError):
        return set()

    if result.returncode != 0:
        return set()

    ids: set[str] = set()
    for line in result.stdout.splitlines():
        if line.startswith("+++"):
            continue
        match = ENTRY_ID_RE.match(line)
        if match:
            ids.add(match.group(1))
    return ids
