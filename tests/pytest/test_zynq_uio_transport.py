from __future__ import annotations

import pytest

from host.hil import Capability, DioEvent, InvalidConfiguration
from host.hil.transports import ZynqUioTransport
from host.hil.transports import register_map as reg


class FakeMmio:
    def __init__(self, backend_id=reg.BACKEND_ID_AX7010):
        self.regs = {
            reg.REG_MAGIC: reg.MAGIC,
            reg.REG_ABI_VERSION: reg.ABI_VERSION,
            reg.REG_BACKEND_ID: backend_id,
            reg.REG_CAPABILITIES: sum(
                1 << reg.CAPABILITY_BITS[cap]
                for cap in (
                    Capability.TIMEBASE,
                    Capability.FORCE_SAFE,
                    Capability.PWM_CAPTURE,
                    Capability.PWM_COMPLEMENTARY_MONITOR,
                    Capability.ABZ_GENERATOR,
                    Capability.SPI_SENSOR_EMULATOR,
                    Capability.DIO_SCHEDULER,
                )
            ),
            reg.REG_TICK_HZ: 100_000_000,
            reg.REG_COUNTER_BITS: 64,
            reg.REG_BUILD_ID: 0x1234,
            reg.REG_CONTROL: reg.CTRL_FORCE_SAFE | reg.CTRL_ABZ_DIRECTION_FORWARD,
            reg.REG_TIMESTAMP_LO: 0x89ABCDEF,
            reg.REG_TIMESTAMP_HI: 0x01234567,
            reg.REG_PWM_SEQ: 7,
            reg.REG_PWM_VALID: 0b111,
            reg.REG_PWM_FAULTS: 0x21,
            reg.REG_EVT_STATUS: 0,
        }
        for ch in range(3):
            base = reg.REG_PWM_BASE + ch * reg.PWM_STRIDE
            self.regs[base] = 5000 + ch
            self.regs[base + 4] = 2500 + ch
            self.regs[base + 8] = 2500

    def read32(self, offset):
        return self.regs.get(offset, 0)

    def write32(self, offset, value):
        self.regs[offset] = value & 0xFFFFFFFF

    def close(self):
        pass


def test_uio_identity_timestamp_pwm_and_health():
    mmio = FakeMmio()
    transport = ZynqUioTransport(
        mmio,
        expected_backend_type="zynq7010_ax7010",
        hardware_revision="ax7010-test",
    )
    identity = transport.read_identity()
    assert identity.backend_type == "zynq7010_ax7010"
    assert Capability.DIO_SCHEDULER in identity.capabilities
    assert transport.read_timestamp().ticks == 0x0123456789ABCDEF
    assert transport.read_pwm(1).period_ticks == 5001
    assert transport.health()["pwm_fault_flags"] == 0x21


def test_uio_force_safe_abz_and_event_fifo_writes():
    mmio = FakeMmio()
    transport = ZynqUioTransport(mmio)

    transport.force_safe(False)
    assert not (mmio.regs[reg.REG_CONTROL] & reg.CTRL_FORCE_SAFE)

    transport.configure_abz(transition_ticks=1234, direction="reverse")
    assert mmio.regs[reg.REG_ABZ_STEP] == 1234
    assert not (
        mmio.regs[reg.REG_CONTROL] & reg.CTRL_ABZ_DIRECTION_FORWARD
    )

    transport.start_abz()
    assert mmio.regs[reg.REG_CONTROL] & reg.CTRL_ABZ_ENABLE

    event = DioEvent(
        event_id=9,
        target_ticks=0x1122334455667788,
        mask=0x0F,
        value=0x05,
    )
    transport.schedule_dio(event)
    assert mmio.regs[reg.REG_EVT_TS_LO] == 0x55667788
    assert mmio.regs[reg.REG_EVT_TS_HI] == 0x11223344
    assert mmio.regs[reg.REG_EVT_ID] == 9
    assert mmio.regs[reg.REG_EVT_PUSH] == 1


def test_uio_rejects_wrong_board_identity_and_unsupported_abz_shape():
    with pytest.raises(InvalidConfiguration, match="does not match"):
        ZynqUioTransport(
            FakeMmio(reg.BACKEND_ID_AXU2CGB),
            expected_backend_type="zynq7010_ax7010",
        )

    transport = ZynqUioTransport(FakeMmio())
    with pytest.raises(InvalidConfiguration, match="initial_phase"):
        transport.configure_abz(transition_ticks=100, initial_phase=1)
