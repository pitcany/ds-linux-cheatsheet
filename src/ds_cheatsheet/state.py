"""Persisted local workflow state."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RecentItem = dict[str, str]


@dataclass(frozen=True)
class AppState:
    """User-local state persisted outside the content YAML."""

    favorites: tuple[str, ...] = ()
    recent: tuple[RecentItem, ...] = field(default_factory=tuple)


def state_path() -> Path:
    """Return the XDG state path for the app."""
    base = os.environ.get("XDG_STATE_HOME")
    root = Path(base).expanduser() if base else Path.home() / ".local" / "state"
    return root / "ds-cheatsheet" / "state.json"


def load_state(path: Path | None = None) -> AppState:
    """Load persisted state, falling back to empty defaults on any problem."""
    target = path or state_path()
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppState()
    if not isinstance(raw, dict):
        return AppState()

    favorites = tuple(item for item in raw.get("favorites", []) if isinstance(item, str))
    recent_raw = raw.get("recent", [])
    recent: list[RecentItem] = []
    if isinstance(recent_raw, list):
        for item in recent_raw:
            if isinstance(item, dict) and isinstance(item.get("id"), str):
                recent.append({"id": item["id"], "at": str(item.get("at", ""))})
    return AppState(favorites=favorites, recent=tuple(recent))


def save_state(state: AppState, path: Path | None = None) -> None:
    """Persist state, creating the state directory lazily."""
    target = path or state_path()
    payload: dict[str, Any] = {
        "favorites": list(state.favorites),
        "recent": list(state.recent),
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    except OSError:
        return


def toggle_favorite(state: AppState, entry_id: str) -> AppState:
    """Return state with ``entry_id`` toggled in favorites."""
    favorites = tuple(item for item in state.favorites if item != entry_id)
    if len(favorites) == len(state.favorites):
        favorites = (*state.favorites, entry_id)
    return AppState(favorites=favorites, recent=state.recent)


def record_recent(state: AppState, entry_id: str, *, at: str | None = None) -> AppState:
    """Return state with ``entry_id`` moved to the front of recent copies."""
    timestamp = at or datetime.now(UTC).isoformat()
    remaining = tuple(item for item in state.recent if item.get("id") != entry_id)
    recent = ({"id": entry_id, "at": timestamp}, *remaining)
    return AppState(favorites=state.favorites, recent=recent[:50])
