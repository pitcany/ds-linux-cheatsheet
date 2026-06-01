"""Keyword and intent search across cheat sheet entries."""

from __future__ import annotations

import re
from collections.abc import Iterable
from difflib import get_close_matches

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


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_.-]+", text.lower())


def _has_prefix_match(token: str, text: str) -> bool:
    if len(token) < 4 or token in text:
        return False
    return re.search(rf"\b{re.escape(token[:3])}\w*", text) is not None


def _has_fuzzy_match(token: str, text: str) -> bool:
    if len(token) < 5 or token in text:
        return False
    return bool(get_close_matches(token, _words(text), n=1, cutoff=0.82))


def _field_score(token: str, text: str, substring_weight: int, prefix_weight: int) -> int:
    if token in text:
        return substring_weight
    if _has_prefix_match(token, text):
        return prefix_weight
    if _has_fuzzy_match(token, text):
        return 1
    return 0


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
        # Title hits dominate. Substring matches outrank prefix/fuzzy matches.
        total += _field_score(token, title_lc, substring_weight=10, prefix_weight=5)
        total += _field_score(token, cmd_lc, substring_weight=6, prefix_weight=3)
        total += _field_score(token, tags_lc, substring_weight=4, prefix_weight=2)
        # General haystack match.
        if token in haystack:
            total += haystack.count(token)
        elif _has_prefix_match(token, haystack) or _has_fuzzy_match(token, haystack):
            total += 1
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


def suggest(entries: list[CommandEntry], query: str, *, limit: int = 5) -> list[str]:
    """Return up to ``limit`` candidate entry ids for an unmatched query."""
    tokens = _tokenize(query)
    if not tokens:
        return []

    candidates: list[tuple[int, str]] = []
    for entry in entries:
        haystack_words = set(_words(entry.search_text))
        close_count = sum(
            1 for token in tokens if get_close_matches(token, list(haystack_words), n=1, cutoff=0.7)
        )
        if close_count:
            candidates.append((close_count, entry.id))

    candidates.sort(key=lambda pair: (-pair[0], pair[1]))
    return [entry_id for _score, entry_id in candidates[:limit]]
