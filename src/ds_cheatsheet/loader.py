"""Load and validate cheat sheet YAML files."""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path

import yaml

from .models import CommandEntry, CommandFile
from .safety import is_dangerous


class CheatSheetLoadError(RuntimeError):
    """Raised when a YAML file is malformed."""


def _default_data_dirs() -> list[Path]:
    """Return candidate data directories in priority order."""
    candidates: list[Path] = []

    env_dir = os.environ.get("DS_CHEATSHEET_DATA_DIR")
    if env_dir:
        candidates.append(Path(env_dir).expanduser())

    here = Path(__file__).resolve()
    repo_data = here.parent.parent.parent / "data" / "commands"
    candidates.append(repo_data)

    try:
        with resources.as_file(resources.files("ds_cheatsheet") / "data" / "commands") as p:
            candidates.append(Path(p))
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    return candidates


def find_data_dir() -> Path:
    """Locate a readable cheat sheet data directory."""
    for candidate in _default_data_dirs():
        if candidate.is_dir():
            return candidate
    raise CheatSheetLoadError(
        "Could not find cheat sheet data directory. "
        "Set DS_CHEATSHEET_DATA_DIR or install the package."
    )


def load_file(path: Path) -> list[CommandEntry]:
    """Load and validate a single YAML cheat sheet file."""
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise CheatSheetLoadError(f"Invalid YAML in {path}: {exc}") from exc

    if raw is None:
        return []

    if not isinstance(raw, dict):
        raise CheatSheetLoadError(f"{path}: top-level must be a mapping.")

    try:
        parsed = CommandFile.model_validate(raw)
    except Exception as exc:
        raise CheatSheetLoadError(f"{path}: schema validation failed — {exc}") from exc

    # Auto-flag dangerous commands so authors don't have to remember.
    enriched: list[CommandEntry] = []
    for entry in parsed.commands:
        if not entry.category:
            entry = entry.model_copy(update={"category": parsed.category})
        if not entry.dangerous and is_dangerous(entry.command):
            entry = entry.model_copy(update={"dangerous": True})
        enriched.append(entry)

    return enriched


def load_all(data_dir: Path | None = None) -> list[CommandEntry]:
    """Load every YAML file in the data directory."""
    base = data_dir or find_data_dir()
    entries: list[CommandEntry] = []
    seen_ids: set[str] = set()

    for yaml_path in sorted(base.glob("*.yaml")):
        for entry in load_file(yaml_path):
            if entry.id in seen_ids:
                raise CheatSheetLoadError(
                    f"Duplicate command id '{entry.id}' in {yaml_path.name}"
                )
            seen_ids.add(entry.id)
            entries.append(entry)

    return entries


def categories(entries: list[CommandEntry]) -> list[str]:
    """Return sorted unique category names."""
    return sorted({e.category for e in entries})
