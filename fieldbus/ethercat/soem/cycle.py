from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
from typing import Callable

from ...core import CommandEvidence, CommandRunner, ToolUnavailable, require_success, run_command


@dataclass(frozen=True)
class SoemCycleMetrics:
    cycles: int
    cycle_ns: int
    expected_wkc: int
    last_wkc: int
    bad_wkc: int
    max_abs_jitter_ns: int
    mean_abs_jitter_ns: float
    deadline_misses: int
    dc_time_ns: int
    slave_count: int

    @classmethod
    def from_json(cls, text: str) -> "SoemCycleMetrics":
        return cls(**json.loads(text.strip().splitlines()[-1]))


class SoemCycleQualifier:
    def __init__(
        self,
        executable: str = "soem_cycle",
        *,
        runner: CommandRunner = run_command,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        self.executable = executable
        self._runner = runner
        self._which = which

    def resolve(self) -> str:
        path = self._which(self.executable)
        if path is None:
            raise ToolUnavailable(f"SOEM cycle tool {self.executable!r} is not installed")
        return path

    def run(
        self,
        interface: str,
        *,
        cycle_us: int = 1000,
        seconds: int = 10,
        timeout_s: float | None = None,
    ) -> tuple[CommandEvidence, SoemCycleMetrics]:
        if not interface or cycle_us <= 0 or seconds <= 0:
            raise ValueError("invalid SOEM cycle arguments")
        evidence = require_success(
            self._runner(
                (self.resolve(), interface, str(cycle_us), str(seconds)),
                timeout_s or (seconds + 10.0),
            ),
            "SOEM cycle qualification",
        )
        return evidence, SoemCycleMetrics.from_json(evidence.stdout)
