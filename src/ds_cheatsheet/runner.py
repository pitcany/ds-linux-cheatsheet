"""Safe command runner.

The runner is intentionally cautious:
- Default policy is to *not* execute. Callers must opt in explicitly.
- Dangerous commands are blocked unless `force=True`.
- Output is captured and returned for display in the TUI.
"""

from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass

from .safety import analyze


@dataclass(frozen=True)
class RunResult:
    """Outcome of a run attempt."""

    command: str
    executed: bool
    returncode: int | None
    stdout: str
    stderr: str
    reason: str


def run(
    command: str,
    *,
    confirm: bool = False,
    force: bool = False,
    timeout: float = 15.0,
) -> RunResult:
    """Run a shell command with safety gates.

    Parameters
    ----------
    command:
        Command line to execute.
    confirm:
        Must be True or the runner refuses to execute.
    force:
        Required to run a command flagged dangerous by :mod:`.safety`.
    timeout:
        Hard timeout in seconds.
    """
    if not command.strip():
        return RunResult(command, False, None, "", "", "Empty command.")

    if not confirm:
        return RunResult(command, False, None, "", "", "Refused: confirmation required.")

    safety = analyze(command)
    if safety.dangerous and not force:
        joined = "; ".join(safety.reasons)
        return RunResult(
            command,
            False,
            None,
            "",
            "",
            f"Refused: dangerous command. {joined}",
        )

    try:
        proc = subprocess.run(
            shlex.split(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return RunResult(command, False, None, "", str(exc), "Command not found.")
    except subprocess.TimeoutExpired:
        return RunResult(command, False, None, "", "", f"Timed out after {timeout}s.")
    except Exception as exc:
        return RunResult(command, False, None, "", str(exc), "Execution error.")

    return RunResult(
        command=command,
        executed=True,
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        reason="ok",
    )
