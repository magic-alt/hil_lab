from __future__ import annotations

from pathlib import Path

import pytest

from host.hil import API_VERSION, BackendIdentity, Capability, HilBackend, InvalidConfiguration
from host.hil.scenario import load_scenario, scenario_from_dict

ROOT = Path(__file__).resolve().parents[2]


class ScenarioBackend(HilBackend):
    def __init__(self, capabilities: frozenset[Capability]):
        self._identity = BackendIdentity(
            backend_type="scenario-test",
            hardware_revision="test",
            firmware_revision="test",
            api_version=API_VERSION,
            capabilities=capabilities,
            tick_hz=100_000_000,
            counter_bits=64,
        )

    @property
    def identity(self) -> BackendIdentity:
        return self._identity

    def force_safe(self, asserted: bool = True) -> None:
        pass

    def health(self):
        return {}


def test_example_scenario_is_ordered_and_contract_valid():
    scenario = load_scenario(ROOT / "lab" / "scenarios" / "smoke_pwm_abz_fault.json")
    assert scenario.name == "smoke-pwm-abz-fault"
    assert scenario.steps[0].at_ticks == 0
    assert scenario.steps[-1].at_ticks == 150_000

    backend = ScenarioBackend(scenario.required_capabilities)
    scenario.validate_against(backend)


def test_scenario_reports_missing_backend_capability():
    scenario = load_scenario(ROOT / "lab" / "scenarios" / "smoke_pwm_abz_fault.json")
    backend = ScenarioBackend(frozenset({Capability.TIMEBASE, Capability.FORCE_SAFE}))
    with pytest.raises(InvalidConfiguration, match="abz_generator"):
        scenario.validate_against(backend)


def test_scenario_rejects_out_of_order_steps():
    document = {
        "version": 1,
        "name": "bad-order",
        "required_capabilities": ["timebase"],
        "steps": [
            {"at_ticks": 20, "action": "one"},
            {"at_ticks": 10, "action": "two"},
        ],
    }
    with pytest.raises(ValueError, match="ordered"):
        scenario_from_dict(document)
