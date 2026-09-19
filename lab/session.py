from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from lab.resources import ResourceLock


@dataclass
class ServoHilSession:
    backend: Any
    resource_lock: ResourceLock
    labgrid_lease: Any | None = None

    def __enter__(self) -> "ServoHilSession":
        self.resource_lock.acquire()
        try:
            if self.labgrid_lease is not None:
                self.labgrid_lease.acquire()
            self.backend.force_safe(True)
            return self
        except Exception:
            if self.labgrid_lease is not None:
                try:
                    self.labgrid_lease.release()
                except Exception:
                    pass
            self.resource_lock.release()
            raise

    def __exit__(self, exc_type, exc, tb) -> None:
        safety_error = None
        try:
            self.backend.force_safe(True)
        except Exception as error:
            safety_error = error
        finally:
            if self.labgrid_lease is not None:
                try:
                    self.labgrid_lease.release()
                finally:
                    self.resource_lock.release()
            else:
                self.resource_lock.release()
        if safety_error is not None and exc is None:
            raise safety_error
