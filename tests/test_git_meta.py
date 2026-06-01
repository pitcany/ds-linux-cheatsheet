from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from ds_cheatsheet.git_meta import recent_entry_ids


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_recent_entry_ids_returns_ids_added_recently(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    data_dir = repo / "data" / "commands"
    data_dir.mkdir(parents=True)
    _git(tmp_path, "init", str(repo))
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (data_dir / "gpu.yaml").write_text(
        """
category: gpu
commands:
  - id: gpu-recent-test
    title: Recent GPU test
    category: gpu
    command: nvidia-smi
    explanation: Show GPUs.
    examples:
      - description: Show GPUs
        command: nvidia-smi
""".lstrip(),
        encoding="utf-8",
    )
    _git(repo, "add", "data/commands/gpu.yaml")
    _git(repo, "commit", "-m", "test: add recent entry")

    assert recent_entry_ids(repo, days=7) == {"gpu-recent-test"}


def test_recent_entry_ids_returns_empty_outside_git_repo(tmp_path: Path) -> None:
    assert recent_entry_ids(tmp_path, days=7) == set()
