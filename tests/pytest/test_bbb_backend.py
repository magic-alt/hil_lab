from __future__ import annotations

from types import SimpleNamespace

import pytest

from host.hil import Capability, InfrastructureError, InvalidConfiguration
from host.hil.backends import BeagleBonePruBackend


class FakeProtocol:
    CAP_TIMEBASE = 1 << 0
    CAP_FORCE_SAFE = 1 << 3
    CAP_PWM_CAPTURE = 1 << 5
    CAP_PWM_COMPLEMENTARY_MONITOR = 1 << 6
    CAP_ABZ_EMULATOR = 1 << 10
    CAP_SCHEDULED_GPIO = 1 << 11
    CAP_SSI_EMULATOR = 1 << 13
    CAP_BISS_EMULATOR = 1 << 14
    CAP_SPI_SENSOR_EMULATOR = 1 << 15

    MSG_HELLO = 1
    MSG_TIME = 2
    MSG_FORCE_SAFE = 4
    MSG_ABZ_CONFIG = 16
    MSG_ABZ_START = 17
    MSG_ABZ_STOP = 18

    ERR_INVALID_ARGUMENT = 1 << 4


class FakeRpc:
    def __init__(self, capabilities: int, firmware: int, tick_hz: int = 200_000_000):
        self.capabilities = capabilities
        self.firmware = firmware
        self.tick_hz = tick_hz
        self.ticks = 100
        self.calls: list[tuple[int, dict[str, int]]] = []

    def request(self, msg_type: int, **kwargs: int):
        self.calls.append((msg_type, kwargs))
        if msg_type == FakeProtocol.MSG_HELLO:
            return SimpleNamespace(
                flags=0,
                arg0=self.capabilities,
                arg1=self.tick_hz,
                arg2=32,
                arg3=self.firmware,
            )
        if msg_type == FakeProtocol.MSG_TIME:
            self.ticks += 5
            return SimpleNamespace(
                flags=0,
                arg0=self.ticks,
                arg1=self.tick_hz,
                arg2=32,
                arg3=0,
            )
        return SimpleNamespace(flags=0, arg0=0, arg1=0, arg2=0, arg3=0)


def make_snapshot(tick_hz: int = 200_000_000):
    channel = [
        SimpleNamespace(
            period_ticks=10_000 + i,
            high_ticks=5_000 + i,
            low_ticks=5_000,
            flags=0x1C,
        )
        for i in range(6)
    ]
    return SimpleNamespace(
        tick_hz=tick_hz,
        event_seq=42,
        running=1,
        fault_flags=0,
        channel=channel,
    )


def make_backend() -> tuple[BeagleBonePruBackend, FakeRpc, FakeRpc]:
    capture = FakeRpc(
        FakeProtocol.CAP_TIMEBASE
        | FakeProtocol.CAP_FORCE_SAFE
        | FakeProtocol.CAP_PWM_CAPTURE
        | FakeProtocol.CAP_PWM_COMPLEMENTARY_MONITOR,
        0x00020000,
    )
    stimulus = FakeRpc(
        FakeProtocol.CAP_TIMEBASE
        | FakeProtocol.CAP_FORCE_SAFE
        | FakeProtocol.CAP_ABZ_EMULATOR
        | FakeProtocol.CAP_SCHEDULED_GPIO
        | FakeProtocol.CAP_SSI_EMULATOR,
        0x00031000,
    )
    backend = BeagleBonePruBackend(
        capture_rpc=capture,
        stimulus_rpc=stimulus,
        snapshot_reader=lambda **_: make_snapshot(),
        protocol=FakeProtocol,
        hardware_revision="test-bbb",
    )
    return backend, capture, stimulus


def test_bbb_capability_mapping_is_fail_closed():
    backend, _, _ = make_backend()
    assert backend.supports(Capability.TIMEBASE)
    assert backend.supports(Capability.PWM_CAPTURE)
    assert backend.supports(Capability.ABZ_GENERATOR)
    assert backend.supports(Capability.SSI_SENSOR_EMULATOR)

    # The current BBB wire ABI has CAP_SCHEDULED_GPIO but no generic masked
    # DIO enqueue command, so the common API must not overclaim this feature.
    assert not backend.supports(Capability.DIO_SCHEDULER)


def test_bbb_reads_real_shared_snapshot_semantics():
    backend, _, _ = make_backend()
    sample = backend.read_pwm(2)
    assert sample.channel == 2
    assert sample.sequence == 42
    assert sample.period_ticks == 10_002
    assert sample.high_ticks == 5_002
    assert sample.valid is True


def test_bbb_timestamp_and_abz_use_rpmsg_commands():
    backend, capture, stimulus = make_backend()

    stamp = backend.read_timestamp()
    assert stamp.tick_hz == 200_000_000
    assert stamp.counter_bits == 32

    backend.configure_abz(
        transition_ticks=4000,
        direction_forward=False,
        initial_phase=2,
        index_interval=4000,
        index_width=1,
    )
    backend.start_abz()
    backend.stop_abz()

    config_calls = [
        kwargs
        for msg, kwargs in stimulus.calls
        if msg == FakeProtocol.MSG_ABZ_CONFIG
    ]
    assert config_calls == [
        {
            "arg0": 4000,
            "arg1": 4000,
            "arg2": 1,
            "arg3": 1 | (2 << 8),
        }
    ]
    assert any(msg == FakeProtocol.MSG_TIME for msg, _ in capture.calls)


def test_bbb_force_safe_asserts_both_prus_and_never_fakes_release():
    backend, capture, stimulus = make_backend()
    backend.force_safe(True)
    assert any(msg == FakeProtocol.MSG_FORCE_SAFE for msg, _ in capture.calls)
    assert any(msg == FakeProtocol.MSG_FORCE_SAFE for msg, _ in stimulus.calls)

    with pytest.raises(InvalidConfiguration, match="no generic FORCE_SAFE deassert"):
        backend.force_safe(False)


def test_bbb_rejects_timestamp_domain_mismatch():
    capture = FakeRpc(
        FakeProtocol.CAP_TIMEBASE | FakeProtocol.CAP_FORCE_SAFE,
        1,
        tick_hz=200_000_000,
    )
    stimulus = FakeRpc(
        FakeProtocol.CAP_TIMEBASE | FakeProtocol.CAP_FORCE_SAFE,
        2,
        tick_hz=100_000_000,
    )
    with pytest.raises(InfrastructureError, match="timestamp metadata mismatch"):
        BeagleBonePruBackend(
            capture_rpc=capture,
            stimulus_rpc=stimulus,
            snapshot_reader=lambda **_: make_snapshot(),
            protocol=FakeProtocol,
        )


def test_bbb_board_runtime_is_importable_as_package():
    from boards.beaglebone_black.host import hil_pru_cli

    assert hil_pru_cli.HilPru is not None
