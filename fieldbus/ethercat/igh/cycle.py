from __future__ import annotations

from dataclasses import dataclass
import json
import shutil
from typing import Callable

from ...core import CommandEvidence, CommandRunner, ToolUnavailable, require_success, run_command


@dataclass(frozen=True)
class EthercatCycleMetrics:
    cycles: int
    cycle_ns: int
    last_wkc: int
    wc_complete_cycles: int
    bad_wkc: int
    max_abs_jitter_ns: int
    mean_abs_jitter_ns: float
    deadline_misses: int
    statusword: int
    operation_enabled_cycles: int
    enable_drive: bool

    @classmethod
    def from_json(cls, text: str) -> "EthercatCycleMetrics":
        data = json.loads(text.strip().splitlines()[-1])
        return cls(**data)


class IghCycleQualifier:
    def __init__(
        self,
        executable: str = "cia402_cycle",
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
            raise ToolUnavailable(f"IgH cycle tool {self.executable!r} is not installed")
        return path

    def run(
        self,
        *,
        position: int,
        vendor_id: int,
        product_code: int,
        cycle_us: int = 1000,
        seconds: int = 10,
        mode: int = 8,
        assign_activate: int = 0x0300,
        enable_drive: bool = False,
        timeout_s: float | None = None,
    ) -> tuple[CommandEvidence, EthercatCycleMetrics]:
        if position < 0 or cycle_us <= 0 or seconds <= 0:
            raise ValueError("invalid EtherCAT cycle arguments")
        if mode not in (8, 9, 10):
            raise ValueError("CiA402 cyclic mode must be CSP=8, CSV=9 or CST=10")
        executable = self.resolve()
        argv = (
            executable,
            str(position),
            hex(vendor_id),
            hex(product_code),
            str(cycle_us),
            str(seconds),
            str(mode),
            hex(assign_activate),
            "1" if enable_drive else "0",
        )
        evidence = require_success(
            self._runner(argv, timeout_s or (seconds + 10.0)),
            "IgH CiA402 cycle qualification",
        )
        return evidence, EthercatCycleMetrics.from_json(evidence.stdout)
