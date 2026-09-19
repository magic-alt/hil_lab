from __future__ import annotations

from dataclasses import dataclass
import subprocess
import time
from typing import Callable, Sequence


class FieldbusError(RuntimeError):
    """Base error for controller-side fieldbus infrastructure."""


class ToolUnavailable(FieldbusError):
    """Required external fieldbus utility is not installed or not discoverable."""


class CommandFailed(FieldbusError):
    """External fieldbus utility returned a non-zero status."""


@dataclass(frozen=True)
class CommandEvidence:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration_ns: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


CommandRunner = Callable[[Sequence[str], float], CommandEvidence]


def run_command(argv: Sequence[str], timeout_s: float = 5.0) -> CommandEvidence:
    if timeout_s <= 0:
        raise ValueError("timeout_s must be > 0")
    started = time.monotonic_ns()
    completed = subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return CommandEvidence(
        argv=tuple(str(v) for v in argv),
        returncode=int(completed.returncode),
        stdout=completed.stdout,
        stderr=completed.stderr,
        duration_ns=time.monotonic_ns() - started,
    )


def require_success(evidence: CommandEvidence, operation: str) -> CommandEvidence:
    if not evidence.ok:
        raise CommandFailed(
            f"{operation} failed rc={evidence.returncode}: {evidence.stderr.strip()}"
        )
    return evidence
