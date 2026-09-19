from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any

try:
    import fcntl
except ImportError:  # pragma: no cover - controller targets are Linux
    fcntl = None


class ResourceBusy(RuntimeError):
    pass


@dataclass(frozen=True)
class BenchResource:
    resource_id: str
    controller: str
    backend: str
    dut: str
    adapter_revision: str
    fieldbus_interface: str | None = None

    def __post_init__(self) -> None:
        for name in ("resource_id", "controller", "backend", "dut", "adapter_revision"):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "controller": self.controller,
            "backend": self.backend,
            "dut": self.dut,
            "adapter_revision": self.adapter_revision,
            "fieldbus_interface": self.fieldbus_interface,
        }


class ResourceLock:
    """Non-destructive local Linux lock used beneath future labgrid allocation."""

    def __init__(self, lock_path: Path, resource_id: str) -> None:
        self.lock_path = lock_path
        self.resource_id = resource_id
        self._file = None

    def acquire(self, *, blocking: bool = False) -> None:
        if fcntl is None:
            raise RuntimeError("resource locking requires Linux fcntl")
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.lock_path.open("a+", encoding="utf-8")
        operation = fcntl.LOCK_EX
        if not blocking:
            operation |= fcntl.LOCK_NB
        try:
            fcntl.flock(handle.fileno(), operation)
        except BlockingIOError as exc:
            handle.close()
            raise ResourceBusy(f"resource {self.resource_id!r} is already locked") from exc

        handle.seek(0)
        handle.truncate()
        json.dump(
            {"resource_id": self.resource_id, "pid": os.getpid()},
            handle,
            sort_keys=True,
        )
        handle.flush()
        self._file = handle

    def release(self) -> None:
        if self._file is None:
            return
        fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        self._file.close()
        self._file = None

    def __enter__(self) -> "ResourceLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
