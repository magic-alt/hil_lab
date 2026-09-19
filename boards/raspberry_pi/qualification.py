from __future__ import annotations

from dataclasses import dataclass
import re
import shutil
from typing import Callable

from fieldbus.core import CommandEvidence, CommandRunner, ToolUnavailable, require_success, run_command


_CYCLIC_RE = re.compile(
    r"Min:\s*(?P<min>-?\d+).*?Avg:\s*(?P<avg>-?\d+).*?Max:\s*(?P<max>-?\d+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CyclictestMetrics:
    min_us: int
    avg_us: int
    max_us: int


def parse_cyclictest_metrics(text: str) -> CyclictestMetrics:
    matches = list(_CYCLIC_RE.finditer(text.replace("\n", " ")))
    if not matches:
        raise ValueError("cyclictest summary not found")
    mins = [int(m.group("min")) for m in matches]
    avgs = [int(m.group("avg")) for m in matches]
    maxs = [int(m.group("max")) for m in matches]
    return CyclictestMetrics(min(mins), round(sum(avgs) / len(avgs)), max(maxs))


class CyclictestQualifier:
    def __init__(
        self,
        executable: str = "cyclictest",
        *,
        runner: CommandRunner = run_command,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.executable = executable
        self._runner = runner
        self._which = which

    def run(
        self,
        *,
        seconds: int = 30,
        interval_us: int = 1000,
        priority: int = 95,
        timeout_s: float | None = None,
    ) -> tuple[CommandEvidence, CyclictestMetrics]:
        if seconds <= 0 or interval_us <= 0 or not 1 <= priority <= 99:
            raise ValueError("invalid cyclictest arguments")
        path = self._which(self.executable)
        if path is None:
            raise ToolUnavailable("cyclictest is not installed")
        evidence = require_success(
            self._runner(
                (
                    path, "-m", "-S", "-p", str(priority), "-i", str(interval_us),
                    "-D", f"{seconds}s",
                ),
                timeout_s or (seconds + 10.0),
            ),
            "cyclictest qualification",
        )
        return evidence, parse_cyclictest_metrics(evidence.stdout)
