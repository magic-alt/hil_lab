from __future__ import annotations

import mmap
import os
import struct
from typing import Any, Mapping, Protocol

from host.hil import (
    API_VERSION,
    BackendIdentity,
    DioEvent,
    InfrastructureError,
    InvalidConfiguration,
    PwmMeasurement,
    Timestamp,
)

from . import register_map as reg


class Mmio32(Protocol):
    def read32(self, offset: int) -> int: ...
    def write32(self, offset: int, value: int) -> None: ...
    def close(self) -> None: ...


class UioMmio:
    def __init__(self, fd: int, mapped: mmap.mmap) -> None:
        self._fd = fd
        self._mapped = mapped

    @classmethod
    def open(cls, device: str, map_size: int = reg.MAP_SIZE) -> "UioMmio":
        if map_size < reg.MAP_SIZE:
            raise ValueError("UIO map must cover the 4 KiB HIL register window")
        fd = os.open(device, os.O_RDWR | os.O_SYNC)
        try:
            mapped = mmap.mmap(
                fd,
                map_size,
                flags=mmap.MAP_SHARED,
                prot=mmap.PROT_READ | mmap.PROT_WRITE,
                offset=0,
            )
        except Exception:
            os.close(fd)
            raise
        return cls(fd, mapped)

    def _check(self, offset: int) -> None:
        if offset < 0 or offset + 4 > len(self._mapped) or (offset & 3):
            raise ValueError(f"invalid MMIO offset 0x{offset:x}")

    def read32(self, offset: int) -> int:
        self._check(offset)
        return struct.unpack_from("<I", self._mapped, offset)[0]

    def write32(self, offset: int, value: int) -> None:
        self._check(offset)
        struct.pack_into("<I", self._mapped, offset, value & 0xFFFFFFFF)

    def close(self) -> None:
        self._mapped.close()
        os.close(self._fd)


class ZynqUioTransport:
    def __init__(
        self,
        mmio: Mmio32,
        *,
        expected_backend_type: str | None = None,
        hardware_revision: str = "uio",
        owns_mmio: bool = False,
    ) -> None:
        self._mmio = mmio
        self._owns_mmio = owns_mmio

        magic = self._mmio.read32(reg.REG_MAGIC)
        abi = self._mmio.read32(reg.REG_ABI_VERSION)
        if magic != reg.MAGIC:
            raise InfrastructureError(
                f"HIL AXI magic 0x{magic:08x}, expected 0x{reg.MAGIC:08x}"
            )
        if (abi >> 16) != (reg.ABI_VERSION >> 16):
            raise InfrastructureError(
                f"incompatible HIL AXI ABI 0x{abi:08x}"
            )

        backend_id = self._mmio.read32(reg.REG_BACKEND_ID)
        try:
            backend_type = reg.BACKEND_TYPES[backend_id]
        except KeyError as exc:
            raise InfrastructureError(
                f"unknown HIL AXI backend id 0x{backend_id:08x}"
            ) from exc

        if expected_backend_type is not None and backend_type != expected_backend_type:
            raise InvalidConfiguration(
                f"UIO backend {backend_type!r} does not match "
                f"{expected_backend_type!r}"
            )

        tick_hz = self._mmio.read32(reg.REG_TICK_HZ)
        counter_bits = self._mmio.read32(reg.REG_COUNTER_BITS)
        if tick_hz <= 0 or counter_bits != 64:
            raise InfrastructureError("invalid HIL AXI timestamp metadata")

        caps = decode = reg.decode_capabilities(
            self._mmio.read32(reg.REG_CAPABILITIES)
        )
        self._identity = BackendIdentity(
            backend_type=backend_type,
            hardware_revision=hardware_revision,
            firmware_revision=f"axi-build-0x{self._mmio.read32(reg.REG_BUILD_ID):08x}",
            api_version=API_VERSION,
            capabilities=decode,
            tick_hz=tick_hz,
            counter_bits=counter_bits,
        )

    @classmethod
    def open(
        cls,
        device: str,
        *,
        expected_backend_type: str | None = None,
        hardware_revision: str = "uio",
        map_size: int = reg.MAP_SIZE,
    ) -> "ZynqUioTransport":
        mmio = UioMmio.open(device, map_size=map_size)
        try:
            return cls(
                mmio,
                expected_backend_type=expected_backend_type,
                hardware_revision=hardware_revision,
                owns_mmio=True,
            )
        except Exception:
            mmio.close()
            raise

    def read_identity(self) -> BackendIdentity:
        return self._identity

    def _control(self) -> int:
        return self._mmio.read32(reg.REG_CONTROL)

    def _write_control(self, value: int) -> None:
        self._mmio.write32(reg.REG_CONTROL, value)

    def read_timestamp(self) -> Timestamp:
        for _ in range(8):
            hi0 = self._mmio.read32(reg.REG_TIMESTAMP_HI)
            lo = self._mmio.read32(reg.REG_TIMESTAMP_LO)
            hi1 = self._mmio.read32(reg.REG_TIMESTAMP_HI)
            if hi0 == hi1:
                return Timestamp(
                    ticks=(hi0 << 32) | lo,
                    tick_hz=self._identity.tick_hz,
                    counter_bits=64,
                )
        raise InfrastructureError("could not obtain stable 64-bit AXI timestamp")

    def force_safe(self, asserted: bool = True) -> None:
        value = self._control()
        if asserted:
            value |= reg.CTRL_FORCE_SAFE
        else:
            value &= ~reg.CTRL_FORCE_SAFE
        self._write_control(value)

    def health(self) -> Mapping[str, Any]:
        status = self._mmio.read32(reg.REG_STATUS)
        event_status = self._mmio.read32(reg.REG_EVT_STATUS)
        return {
            "control": self._control(),
            "status": status,
            "event_status": event_status,
            "event_queue_level": (event_status >> 8) & 0xFFFF,
            "event_queue_full": bool(event_status & reg.EVT_STATUS_FULL),
            "event_queue_overflow": bool(event_status & reg.EVT_STATUS_OVERFLOW),
            "event_queue_order_error": bool(
                event_status & reg.EVT_STATUS_ORDER_ERROR
            ),
            "pwm_fault_flags": self._mmio.read32(reg.REG_PWM_FAULTS) & 0x3F,
        }

    def read_pwm(self, channel: int) -> PwmMeasurement:
        if not 0 <= channel < 3:
            raise InvalidConfiguration("Zynq AXI PWM channel must be 0..2")
        base = reg.REG_PWM_BASE + channel * reg.PWM_STRIDE
        valid_bits = self._mmio.read32(reg.REG_PWM_VALID)
        return PwmMeasurement(
            channel=channel,
            sequence=self._mmio.read32(reg.REG_PWM_SEQ),
            period_ticks=self._mmio.read32(base + 0x0),
            high_ticks=self._mmio.read32(base + 0x4),
            low_ticks=self._mmio.read32(base + 0x8),
            valid=bool(valid_bits & (1 << channel)),
            overflow=False,
        )

    def configure_abz(self, **config: Any) -> None:
        transition_ticks = int(
            config.get("transition_ticks", config.get("step_period_ticks", 0))
        )
        if transition_ticks <= 0:
            raise InvalidConfiguration("ABZ transition_ticks must be > 0")

        if int(config.get("initial_phase", 0)) != 0:
            raise InvalidConfiguration(
                "AXI digital core v1 supports initial_phase=0 only"
            )
        if int(config.get("index_interval", config.get("index_interval_edges", 0))) != 0:
            raise InvalidConfiguration(
                "AXI digital core v1 has compile-time index period only"
            )

        self._mmio.write32(reg.REG_ABZ_STEP, transition_ticks)
        value = self._control()
        direction_forward = config.get(
            "direction_forward",
            config.get("direction", "forward") != "reverse",
        )
        if direction_forward:
            value |= reg.CTRL_ABZ_DIRECTION_FORWARD
        else:
            value &= ~reg.CTRL_ABZ_DIRECTION_FORWARD
        self._write_control(value)

    def start_abz(self) -> None:
        value = self._control() | reg.CTRL_HIL_ENABLE | reg.CTRL_ABZ_ENABLE
        value &= ~reg.CTRL_FORCE_SAFE
        self._write_control(value)

    def stop_abz(self) -> None:
        self._write_control(self._control() & ~reg.CTRL_ABZ_ENABLE)

    def schedule_dio(self, event: DioEvent) -> None:
        status = self._mmio.read32(reg.REG_EVT_STATUS)
        if status & reg.EVT_STATUS_FULL:
            raise InfrastructureError("HIL AXI event FIFO is full")
        self._mmio.write32(reg.REG_EVT_TS_LO, event.target_ticks & 0xFFFFFFFF)
        self._mmio.write32(reg.REG_EVT_TS_HI, (event.target_ticks >> 32) & 0xFFFFFFFF)
        self._mmio.write32(reg.REG_EVT_MASK, event.mask)
        self._mmio.write32(reg.REG_EVT_VALUE, event.value)
        self._mmio.write32(reg.REG_EVT_ID, event.event_id)
        self._mmio.write32(reg.REG_EVT_PUSH, 1)

    def clear_faults(self) -> None:
        self._write_control(self._control() | reg.CTRL_CLEAR_FAULTS)

    def close(self) -> None:
        if self._owns_mmio:
            self._mmio.close()

    def __enter__(self) -> "ZynqUioTransport":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
