"""Physical HIL bench resource definitions and locking."""

from .model import BenchResource, ResourceBusy, ResourceLock

__all__ = ["BenchResource", "ResourceBusy", "ResourceLock"]
