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


class SoemSlaveInfo:
    """Adapter for the SOEM slaveinfo example/utility.

    The executable path is configurable because distributions and local SOEM
    builds do not install a universal command name/location.
    """

    def __init__(
        self,
        executable: str = "slaveinfo",
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
                f"SOEM slaveinfo utility {self.executable!r} is not installed"
            )
        return path

    def scan(self, interface: str, timeout_s: float = 10.0) -> CommandEvidence:
        if not interface:
            raise ValueError("interface must be non-empty")
        executable = self.resolve()
        return require_success(
            self._runner((executable, interface), timeout_s),
            "SOEM slaveinfo",
        )
