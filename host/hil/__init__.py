"""Backend-neutral HIL contract and scenario helpers."""

from .core import (
    API_VERSION,
    BackendIdentity,
    Capability,
    DioEvent,
    HilBackend,
    HilError,
    InfrastructureError,
    InvalidConfiguration,
    PwmMeasurement,
    Timestamp,
    UnsupportedCapability,
)
from .scenario import Scenario, ScenarioStep, load_scenario, scenario_from_dict

__all__ = [
    "API_VERSION",
    "BackendIdentity",
    "Capability",
    "DioEvent",
    "HilBackend",
    "HilError",
    "InfrastructureError",
    "InvalidConfiguration",
    "PwmMeasurement",
    "Timestamp",
    "UnsupportedCapability",
    "Scenario",
    "ScenarioStep",
    "load_scenario",
    "scenario_from_dict",
]
