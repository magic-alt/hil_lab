from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
import shutil
from typing import Callable, Iterable


DEFAULT_TOOLS = (
    "cyclictest",
    "ethercat",
    "slaveinfo",
    "ip",
    "cansend",
    "candump",
)


@dataclass(frozen=True)
class ToolProbe:
    name: str
    path: str | None

    @property
    def available(self) -> bool:
        return self.path is not None


@dataclass(frozen=True)
class ControllerEnvironment:
    system: str
    machine: str
    release: str
    kernel_version: str
    preempt_rt_hint: bool
    network_interfaces: tuple[str, ...]
    tools: tuple[ToolProbe, ...]

    def tool(self, name: str) -> ToolProbe:
        for item in self.tools:
            if item.name == name:
                return item
        raise KeyError(name)


def probe_controller_environment(
    *,
    tools: Iterable[str] = DEFAULT_TOOLS,
    sysfs_net: Path = Path("/sys/class/net"),
    which: Callable[[str], str | None] = shutil.which,
) -> ControllerEnvironment:
    uname = platform.uname()
    version_text = f"{uname.version} {uname.release}".upper()
    preempt_rt = "PREEMPT_RT" in version_text or "PREEMPT RT" in version_text

    if sysfs_net.exists():
        interfaces = tuple(
            sorted(path.name for path in sysfs_net.iterdir() if path.name)
        )
    else:
        interfaces = tuple()

    probes = tuple(ToolProbe(name=name, path=which(name)) for name in tools)

    return ControllerEnvironment(
        system=uname.system,
        machine=uname.machine,
        release=uname.release,
        kernel_version=uname.version,
        preempt_rt_hint=preempt_rt,
        network_interfaces=interfaces,
        tools=probes,
    )
