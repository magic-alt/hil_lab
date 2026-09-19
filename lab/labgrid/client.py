from __future__ import annotations

import shutil
from typing import Callable

from fieldbus.core import CommandEvidence, CommandRunner, ToolUnavailable, require_success, run_command


class LabgridPlaceLease:
    def __init__(
        self,
        place: str,
        *,
        executable: str = "labgrid-client",
        runner: CommandRunner = run_command,
        which: Callable[[str], str | None] = shutil.which,
    ) -> None:
        if not place:
            raise ValueError("labgrid place must be non-empty")
        self.place = place
        self.executable = executable
        self._runner = runner
        self._which = which
        self.acquired = False

    def _exe(self) -> str:
        path = self._which(self.executable)
        if path is None:
            raise ToolUnavailable(f"labgrid client {self.executable!r} is not installed")
        return path

    def acquire(self, timeout_s: float = 10.0) -> CommandEvidence:
        evidence = require_success(
            self._runner((self._exe(), "-p", self.place, "acquire"), timeout_s),
            "labgrid acquire",
        )
        self.acquired = True
        return evidence

    def show(self, timeout_s: float = 10.0) -> CommandEvidence:
        return require_success(
            self._runner((self._exe(), "-p", self.place, "show"), timeout_s),
            "labgrid show",
        )

    def release(self, timeout_s: float = 10.0) -> CommandEvidence | None:
        if not self.acquired:
            return None
        try:
            return require_success(
                self._runner((self._exe(), "-p", self.place, "release"), timeout_s),
                "labgrid release",
            )
        finally:
            self.acquired = False

    def __enter__(self) -> "LabgridPlaceLease":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
