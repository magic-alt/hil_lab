from __future__ import annotations

import pytest

from host.hil import (
    API_VERSION,
    BackendIdentity,
    Capability,
    DioEvent,
    HilBackend,
    InvalidConfiguration,
    PwmMeasurement,
    Timestamp,
    UnsupportedCapability,
)


class FakeBackend(HilBackend):
    def __init__(self, capabilities: frozenset[Capability]):
        self._identity = BackendIdentity(
            backend_type="fake",
            hardware_revision="test",
            firmware_revision="test",
            api_version=API_VERSION,
            capabilities=capabilities,
            tick_hz=100_000_000,
            counter_bits=64,
        )
        self.safe = True

    @property
    def identity(self) -> BackendIdentity:
        return self._identity

    def force_safe(self, asserted: bool = True) -> None:
        self.safe = asserted

    def health(self):
        return {"transport_errors": 0}

    def read_pwm(self, channel: int) -> PwmMeasurement:
        self.require(Capability.PWM_CAPTURE)
        return PwmMeasurement(
            channel=channel,
            sequence=1,
            period_ticks=5000,
            high_ticks=2500,
            low_ticks=2500,
        )

    def schedule_dio(self, event: DioEvent) -> None:
        self.require(Capability.DIO_SCHEDULER)


def test_timestamp_preserves_ticks_and_metadata():
    stamp = Timestamp(ticks=25, tick_hz=100_000_000, counter_bits=64)
    assert stamp.ticks == 25
    assert stamp.seconds == pytest.approx(250e-9)


def test_minimum_backend_contract_requires_timebase_and_force_safe():
    backend = FakeBackend(
        frozenset({Capability.TIMEBASE, Capability.FORCE_SAFE, Capability.PWM_CAPTURE})
    )
    backend.validate_contract()
    backend.force_safe(False)
    assert backend.safe is False
    assert backend.read_pwm(0).period_ticks == 5000


def test_contract_rejects_missing_required_capability():
    backend = FakeBackend(frozenset({Capability.TIMEBASE}))
    with pytest.raises(InvalidConfiguration, match="force_safe"):
        backend.validate_contract()


def test_unsupported_capability_is_explicit():
    backend = FakeBackend(frozenset({Capability.TIMEBASE, Capability.FORCE_SAFE}))
    with pytest.raises(UnsupportedCapability) as exc:
        backend.read_pwm(0)
    assert exc.value.capability is Capability.PWM_CAPTURE


def test_dio_event_rejects_negative_timestamp():
    with pytest.raises(ValueError, match="target_ticks"):
        DioEvent(event_id=1, target_ticks=-1, mask=1, value=1)
