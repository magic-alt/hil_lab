from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .core import Capability, HilBackend, InvalidConfiguration

SCENARIO_VERSION = 1


@dataclass(frozen=True)
class ScenarioStep:
    at_ticks: int
    action: str
    args: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.at_ticks < 0:
            raise ValueError("at_ticks must be non-negative")
        if not self.action:
            raise ValueError("action must be non-empty")


@dataclass(frozen=True)
class Scenario:
    name: str
    required_capabilities: frozenset[Capability]
    steps: tuple[ScenarioStep, ...]
    version: int = SCENARIO_VERSION

    def validate_against(self, backend: HilBackend) -> None:
        missing = self.required_capabilities - backend.identity.capabilities
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise InvalidConfiguration(
                f"scenario {self.name!r} requires unsupported capabilities: {names}"
            )


def _capability(value: str) -> Capability:
    try:
        return Capability(value)
    except ValueError as exc:
        raise ValueError(f"unknown capability in scenario: {value}") from exc


def scenario_from_dict(document: Mapping[str, Any]) -> Scenario:
    version = document.get("version")
    if version != SCENARIO_VERSION:
        raise ValueError(
            f"unsupported scenario version {version!r}; expected {SCENARIO_VERSION}"
        )

    name = document.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("scenario name must be a non-empty string")

    raw_caps = document.get("required_capabilities", [])
    if not isinstance(raw_caps, list) or not all(isinstance(v, str) for v in raw_caps):
        raise ValueError("required_capabilities must be a list of strings")
    capabilities = frozenset(_capability(value) for value in raw_caps)

    raw_steps = document.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("steps must be a non-empty list")

    steps: list[ScenarioStep] = []
    previous_tick = -1
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise ValueError(f"step {index} must be an object")
        at_ticks = raw.get("at_ticks")
        action = raw.get("action")
        args = raw.get("args", {})
        if not isinstance(at_ticks, int):
            raise ValueError(f"step {index} at_ticks must be an integer")
        if not isinstance(action, str) or not action:
            raise ValueError(f"step {index} action must be a non-empty string")
        if not isinstance(args, dict):
            raise ValueError(f"step {index} args must be an object")
        if at_ticks < previous_tick:
            raise ValueError("scenario steps must be ordered by at_ticks")
        previous_tick = at_ticks
        steps.append(ScenarioStep(at_ticks=at_ticks, action=action, args=args))

    return Scenario(
        name=name,
        required_capabilities=capabilities,
        steps=tuple(steps),
        version=version,
    )


def load_scenario(path: str | Path) -> Scenario:
    with Path(path).open("r", encoding="utf-8") as handle:
        document = json.load(handle)
    if not isinstance(document, dict):
        raise ValueError("scenario root must be an object")
    return scenario_from_dict(document)
