"""Detect dangerous shell command patterns.

Local, regex-based; no network calls. Used both for flagging entries at load
time and for guarding the optional command runner.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

DANGEROUS_PATTERNS: list[tuple[str, str]] = [
    (r"\brm\s+(-[rRfF]+\s+|-[rRfF]+\b)", "Recursive/forceful rm — can destroy data."),
    (r"\brm\s+-rf\s+/", "rm -rf at filesystem root — catastrophic."),
    (r"\bchmod\s+-R\b", "Recursive chmod — wide permission changes."),
    (r"\bchown\s+-R\b", "Recursive chown — wide ownership changes."),
    (r"\bdd\s+if=", "dd can overwrite raw devices."),
    (r"\bmkfs(\.\w+)?\b", "mkfs formats a filesystem."),
    (r"\bsudo\b", "sudo escalates privileges."),
    (r":\(\)\s*\{.*\}\s*;:", "Fork bomb."),
    (r">\s*/dev/sd[a-z]", "Writing directly to a block device."),
    (r"\bshred\b", "shred irreversibly destroys files."),
    (r"\bwget\s+.+\|\s*sh\b", "Piping remote content to a shell."),
    (r"\bcurl\s+[^|]+\|\s*(sh|bash)\b", "Piping remote content to a shell."),
    (r"\bgit\s+push\s+--force\b", "Force push can rewrite shared history."),
    (r"\bgit\s+reset\s+--hard\b", "Hard reset discards local changes."),
    (r"\bdocker\s+system\s+prune\s+-a\b", "Removes all unused Docker data."),
    (r"\bkill\s+-9\s+-1\b", "Sends SIGKILL to all processes."),
    (r"\btruncate\s+-s\s*0\b", "Truncates files to zero length."),
]

_COMPILED: list[tuple[re.Pattern[str], str]] = [
    (re.compile(pat), reason) for pat, reason in DANGEROUS_PATTERNS
]


@dataclass(frozen=True)
class SafetyReport:
    """Result of analysing a command string."""

    command: str
    dangerous: bool
    reasons: tuple[str, ...]


def analyze(command: str) -> SafetyReport:
    """Inspect a shell command and return matched safety reasons."""
    reasons: list[str] = []
    for regex, reason in _COMPILED:
        if regex.search(command):
            reasons.append(reason)
    return SafetyReport(command=command, dangerous=bool(reasons), reasons=tuple(reasons))


def is_dangerous(command: str) -> bool:
    """Convenience boolean wrapper around :func:`analyze`."""
    return analyze(command).dangerous
