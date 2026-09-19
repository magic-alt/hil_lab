from __future__ import annotations

import shutil
from typing import Callable

from ...core import (
    CommandEvidence,
    CommandRunner,
    ToolUnavailable,
    require_success,
    run_command,
)


class IghEthercatCli:
    """Thin evidence-preserving adapter for the IgH `ethercat` CLI.

    This wrapper is intentionally diagnostic/control-plane only. A successful
    CLI probe is not proof of 1 ms cyclic/DC performance.
    """

    def __init__(
        self,
        executable: str = "ethercat",
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
            raise ToolUnavailable(
                f"IgH EtherCAT CLI {self.executable!r} is not installed"
            )
        return path

    def available(self) -> bool:
        return self._which(self.executable) is not None

    def master_status(self, timeout_s: float = 5.0) -> CommandEvidence:
        executable = self.resolve()
        return require_success(
            self._runner((executable, "master"), timeout_s),
            "IgH ethercat master",
        )

    def scan_slaves(self, timeout_s: float = 5.0) -> tuple[CommandEvidence, tuple[str, ...]]:
        executable = self.resolve()
        evidence = require_success(
            self._runner((executable, "slaves"), timeout_s),
            "IgH ethercat slaves",
        )
        slaves = tuple(
            line.strip()
            for line in evidence.stdout.splitlines()
            if line.strip()
        )
        return evidence, slaves
