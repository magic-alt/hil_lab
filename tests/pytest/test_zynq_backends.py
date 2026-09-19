from __future__ import annotations

import pytest

from host.hil import (
    API_VERSION,
    BackendIdentity,
    Capability,
    DioEvent,
    InfrastructureError,
    InvalidConfiguration,
    PwmMeasurement,
    Timestamp,
)
from host.hil.backends import Ax7010Backend, Axu2cgbBackend


class FakeTransport:
    def __init__(self, backend_type: str):
        self.identity = BackendIdentity(
            backend_type=backend_type,
            hardware_revision="test",
            firmware_revision="bitstream-test",
            api_version=API_VERSION,
            capabilities=frozenset(
                {
                    Capability.TIMEBASE,
                    Capability.FORCE_SAFE,
                    Capability.PWM_CAPTURE,
                    Capability.ABZ_GENERATOR,
                    Capability.DIO_SCHEDULER,
                }
            ),
            tick_hz=100_000_000,
            counter_bits=64,
        )
        self.safe = True
        self.events: list[DioEvent] = []
        self.abz_started = False

    def read_identity(self):
        return self.identity

    def read_timestamp(self):
        return Timestamp(123, 100_000_000, 64)

    def force_safe(self, asserted=True):
        self.safe = asserted

    def health(self):
        return {"transport": "fake", "safe": self.safe}

    def read_pwm(self, channel):
        return PwmMeasurement(channel, 7, 5000, 2500, 2500)

    def configure_abz(self, **config):
        self.abz_config = config

    def start_abz(self):
        self.abz_started = True

    def stop_abz(self):
        self.abz_started = False

    def schedule_dio(self, event):
        self.events.append(event)


def test_ax7010_backend_dispatches_only_negotiated_transport():
    transport = FakeTransport("zynq7010_ax7010")
    backend = Ax7010Backend(transport)

    assert backend.read_timestamp().ticks == 123
    assert backend.read_pwm(1).period_ticks == 5000

    backend.configure_abz(transition_ticks=100)
    backend.start_abz()
    assert transport.abz_started
    backend.stop_abz()

    event = DioEvent(event_id=3, target_ticks=1000, mask=0x3, value=0x1)
    backend.schedule_dio(event)
    assert transport.events == [event]


def test_axu2cgb_backend_rejects_wrong_hardware_identity():
    with pytest.raises(InvalidConfiguration, match="does not match"):
        Axu2cgbBackend(FakeTransport("zynq7010_ax7010"))


def test_zynq_declared_capability_without_transport_method_is_infrastructure_error():
    transport = FakeTransport("zynq_axu2cgb")
    transport.read_pwm = None
    backend = Axu2cgbBackend(transport)

    with pytest.raises(InfrastructureError, match="has no read_pwm"):
        backend.read_pwm(0)


def test_zynq_does_not_offer_hardwareless_factory_or_gpio_fallback():
    with pytest.raises(TypeError):
        Ax7010Backend()
