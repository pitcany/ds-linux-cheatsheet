"""Keyword and intent search across cheat sheet entries."""

from __future__ import annotations

import re
from collections.abc import Iterable

from .models import CommandEntry

# Intent synonyms: maps a user phrase (lowercased) to extra search terms that
# should also be matched. Keeps the YAML clean while making natural queries work.
INTENT_SYNONYMS: dict[str, tuple[str, ...]] = {
    "find large files": ("du", "find", "size", "largest", "ncdu"),
    "search logs": ("grep", "rg", "tail", "less", "journalctl"),
    "kill process": ("kill", "pkill", "killall", "pgrep"),
    "copy files to server": ("rsync", "scp", "ssh"),
    "split csv": ("split", "csvkit", "awk", "head", "wc"),
    "monitor gpu": ("nvidia-smi", "nvtop", "gpu"),
    "tmux new session": ("tmux", "new", "session"),
    "grep recursively": ("grep", "rg", "-r", "recursive"),
    "remote shell": ("ssh", "remote"),
    "disk space": ("df", "du", "ncdu"),
    "running processes": ("ps", "top", "htop", "btop"),
    "compress files": ("tar", "gzip", "zstd", "xz"),
    "extract archive": ("tar", "unzip", "gunzip"),
    "watch file": ("tail", "less", "watch"),
}


def _tokenize(query: str) -> list[str]:
    return [t for t in re.split(r"\s+", query.strip().lower()) if t]


def _expand(query: str) -> list[str]:
    base = _tokenize(query)
    expansions: list[str] = list(base)
    q = query.strip().lower()
    if q in INTENT_SYNONYMS:
        expansions.extend(INTENT_SYNONYMS[q])
    else:
        for phrase, extras in INTENT_SYNONYMS.items():
            if phrase in q:
                expansions.extend(extras)
    seen: set[str] = set()
    deduped: list[str] = []
    for token in expansions:
        if token not in seen:
            seen.add(token)
            deduped.append(token)
    return deduped


def score(entry: CommandEntry, tokens: Iterable[str]) -> int:
    """Return a coarse relevance score for ranking."""
    haystack = entry.search_text
    title_lc = entry.title.lower()
    cmd_lc = entry.command.lower()
    tags_lc = " ".join(entry.tags).lower()

    total = 0
    for token in tokens:
        if not token:
            continue
        # Title hits dominate.
        if token in title_lc:
            total += 10
        if token in cmd_lc:
            total += 6
        if token in tags_lc:
            total += 4
        # General haystack match.
        count = haystack.count(token)
        total += count
    return total


def search(
    entries: list[CommandEntry],
    query: str,
    *,
    category: str | None = None,
) -> list[CommandEntry]:
    """Return entries matching the query, ranked by relevance."""
    pool = [e for e in entries if category is None or e.category == category]

    if not query.strip():
        return sorted(pool, key=lambda e: (e.category, e.title.lower()))

    tokens = _expand(query)
    scored = [(score(e, tokens), e) for e in pool]
    matches = [(s, e) for s, e in scored if s > 0]
    matches.sort(key=lambda pair: (-pair[0], pair[1].title.lower()))
    return [e for _, e in matches]
