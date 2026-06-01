"""Local, rule-based command explainer. No network calls."""

from __future__ import annotations

import shlex
from dataclasses import dataclass

from .safety import analyze

# Short descriptions for a curated set of common commands. Anything not listed
# falls back to a generic "external command" label.
COMMAND_DESCRIPTIONS: dict[str, str] = {
    "ls": "List directory contents.",
    "cd": "Change current working directory.",
    "cp": "Copy files and directories.",
    "mv": "Move or rename files.",
    "rm": "Remove files or directories.",
    "mkdir": "Create directories.",
    "rmdir": "Remove empty directories.",
    "cat": "Concatenate and print files.",
    "less": "Pager for viewing file contents.",
    "head": "Output the first part of files.",
    "tail": "Output the last part of files.",
    "grep": "Search text using patterns.",
    "rg": "ripgrep — fast recursive grep.",
    "find": "Walk a file hierarchy and match files.",
    "fd": "Simple, fast alternative to find.",
    "awk": "Pattern scanning and processing language.",
    "sed": "Stream editor for filtering and transforming text.",
    "xargs": "Build and execute command lines from standard input.",
    "ssh": "OpenSSH remote login client.",
    "scp": "Secure copy (uses SSH).",
    "rsync": "Fast, incremental file transfer.",
    "git": "Distributed version control system.",
    "docker": "Container engine CLI.",
    "tmux": "Terminal multiplexer.",
    "screen": "Terminal multiplexer (older).",
    "conda": "Conda package and environment manager.",
    "pip": "Python package installer.",
    "python": "Python interpreter.",
    "python3": "Python 3 interpreter.",
    "jq": "Command-line JSON processor.",
    "csvkit": "Suite of CSV command-line utilities.",
    "csvcut": "Filter and reorder CSV columns.",
    "csvgrep": "Search CSV rows by pattern.",
    "csvstat": "Summary statistics for CSV columns.",
    "ps": "Report a snapshot of current processes.",
    "top": "Display Linux processes.",
    "htop": "Interactive process viewer.",
    "btop": "Modern resource monitor.",
    "kill": "Send a signal to a process.",
    "pkill": "Signal processes based on name.",
    "killall": "Kill processes by name.",
    "pgrep": "Look up processes based on name.",
    "df": "Report file system disk space usage.",
    "du": "Estimate file space usage.",
    "ncdu": "NCurses disk usage analyzer.",
    "nvidia-smi": "NVIDIA System Management Interface.",
    "nvtop": "Interactive NVIDIA / AMD GPU process viewer.",
    "ip": "Show / manipulate routing, devices, policy.",
    "ss": "Investigate sockets (modern netstat).",
    "netstat": "Network connections and routing tables.",
    "curl": "Transfer data from or to a server.",
    "wget": "Non-interactive network downloader.",
    "dig": "DNS lookup utility.",
    "nslookup": "Query DNS records.",
    "tar": "Archive utility.",
    "zip": "Package and compress files.",
    "unzip": "Extract zip archives.",
    "gzip": "Compress files (.gz).",
    "gunzip": "Decompress .gz files.",
    "zstd": "Fast lossless compression.",
    "echo": "Display a line of text.",
    "watch": "Execute a program periodically, showing output.",
    "env": "Run a program in a modified environment.",
    "export": "Set environment variables (shell builtin).",
    "source": "Execute commands from a file in the current shell.",
}

# Generic flag descriptions used when a flag isn't explicitly documented.
GENERIC_FLAG_HINTS: dict[str, str] = {
    "-r": "Often: recursive.",
    "-R": "Often: recursive (capital).",
    "-v": "Often: verbose.",
    "-h": "Often: human-readable or help.",
    "-a": "Often: all (include hidden).",
    "-l": "Often: long / list format.",
    "-f": "Often: force.",
    "-n": "Often: dry-run or number.",
    "-q": "Often: quiet.",
    "-i": "Often: interactive or insensitive.",
    "-o": "Often: output file.",
    "-c": "Often: command or count.",
    "-e": "Often: expression or enable.",
    "-x": "Often: trace or extract.",
    "-p": "Often: port or preserve.",
}


@dataclass(frozen=True)
class Token:
    """A single parsed component of a shell command line."""

    value: str
    kind: str  # "command", "flag", "value", "operator", "pipe"
    description: str


@dataclass(frozen=True)
class Explanation:
    """The result of explaining a command."""

    command: str
    tokens: tuple[Token, ...]
    notes: tuple[str, ...]
    dangerous: bool
    danger_reasons: tuple[str, ...]


_PIPE_LIKE = {"|", "||", "&&", ";", ">", ">>", "<", "2>", "2>>", "&"}


def _describe_command(name: str) -> str:
    return COMMAND_DESCRIPTIONS.get(name, f"External command `{name}`.")


def _describe_flag(flag: str) -> str:
    if flag in GENERIC_FLAG_HINTS:
        return GENERIC_FLAG_HINTS[flag]
    if flag.startswith("--"):
        return "Long-form option."
    return "Short option."


def explain(command: str) -> Explanation:
    """Break a shell command into tokens with short descriptions.

    Intentionally simple: we treat each whitespace-delimited piece as a token,
    classify by leading character, and look up known descriptions.
    """
    command = command.strip()
    try:
        pieces = shlex.split(command, posix=True)
    except ValueError:
        # Unbalanced quoting — fall back to naive split.
        pieces = command.split()

    tokens: list[Token] = []
    notes: list[str] = []
    expecting_command = True

    for piece in pieces:
        if piece in _PIPE_LIKE:
            tokens.append(
                Token(value=piece, kind="operator", description=f"Shell operator `{piece}`.")
            )
            expecting_command = True
            continue

        if expecting_command and not piece.startswith("-"):
            tokens.append(
                Token(value=piece, kind="command", description=_describe_command(piece))
            )
            expecting_command = False
            continue

        if piece.startswith("--") and "=" in piece:
            flag, value = piece.split("=", 1)
            tokens.append(Token(value=flag, kind="flag", description=_describe_flag(flag)))
            tokens.append(
                Token(value=value, kind="value", description=f"Value for `{flag}`.")
            )
            continue

        if piece.startswith("-"):
            tokens.append(Token(value=piece, kind="flag", description=_describe_flag(piece)))
            continue

        tokens.append(Token(value=piece, kind="value", description="Positional argument."))

    if not tokens:
        notes.append("No tokens parsed — empty command.")

    safety = analyze(command)
    if safety.dangerous:
        notes.append("This command contains potentially destructive patterns.")

    return Explanation(
        command=command,
        tokens=tuple(tokens),
        notes=tuple(notes),
        dangerous=safety.dangerous,
        danger_reasons=safety.reasons,
    )
