"""Placeholder discovery and substitution for command templates."""

from __future__ import annotations

import re

PLACEHOLDER_RE = re.compile(r"<([A-Za-z_][A-Za-z0-9_-]*)>")


def find_placeholders(command: str) -> list[str]:
    """Return placeholder names in order of first appearance, deduped."""
    seen: set[str] = set()
    placeholders: list[str] = []
    for match in PLACEHOLDER_RE.finditer(command):
        name = match.group(1)
        if name not in seen:
            seen.add(name)
            placeholders.append(name)
    return placeholders


def substitute(command: str, mapping: dict[str, str]) -> str:
    """Replace <name> tokens. Missing keys leave the token intact."""

    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        return mapping.get(name, match.group(0))

    return PLACEHOLDER_RE.sub(replace, command)
