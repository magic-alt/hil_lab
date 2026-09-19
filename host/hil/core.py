from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, FrozenSet, Mapping

API_VERSION = "0.1"


class Capability(str, Enum):
    TIMEBASE = "timebase"
    FORCE_SAFE = "force_safe"
    PWM_CAPTURE = "pwm_capture"
    PWM_GENERATOR = "pwm_generator"
    PWM_COMPLEMENTARY_MONITOR = "pwm_complementary_monitor"
    ABZ_GENERATOR = "abz_generator"
    ABZ_CAPTURE = "abz_capture"
    SSI_SENSOR_EMULATOR = "ssi_sensor_emulator"
    SSI_SENSOR_CAPTURE = "ssi_sensor_capture"
    BISS_SENSOR_EMULATOR = "biss_sensor_emulator"
    SPI_SENSOR_EMULATOR = "spi_sensor_emulator"
    DIO_SCHEDULER = "dio_scheduler"
    FAULT_INJECTION = "fault_injection"
    DAC_FEEDBACK = "dac_feedback"
    PMSM_PLANT_LITE = "pmsm_plant_lite"
    PMSM_PLANT = "pmsm_plant"
    DUAL_INERTIA_PLANT = "dual_inertia_plant"


REQUIRED_BACKEND_CAPABILITIES: FrozenSet[Capability] = frozenset(
    {Capability.TIMEBASE, Capability.FORCE_SAFE}
)


class HilError(RuntimeError):
    """Base error for host/backend contract failures."""


class UnsupportedCapability(HilError):
    def __init__(self, capability: Capability):
        super().__init__(f"backend does not support capability: {capability.value}")
        self.capability = capability


class InfrastructureError(HilError):
    """Transport, backend or bench infrastructure failure."""


class InvalidConfiguration(HilError):
    """Configuration violates the backend contract or backend limits."""


@dataclass(frozen=True)
class Timestamp:
    ticks: int
    tick_hz: int
    counter_bits: int

    def __post_init__(self) -> None:
        if self.ticks < 0:
            raise ValueError("ticks must be non-negative")
        if self.tick_hz <= 0:
            raise ValueError("tick_hz must be positive")
        if self.counter_bits <= 0:
            raise ValueError("counter_bits must be positive")

    @property
    def seconds(self) -> float:
        return self.ticks / self.tick_hz


@dataclass(frozen=True)
class BackendIdentity:
    backend_type: str
    hardware_revision: str
    firmware_revision: str
    api_version: str
    capabilities: FrozenSet[Capability]
    tick_hz: int
    counter_bits: int

    def __post_init__(self) -> None:
        if not self.backend_type:
            raise ValueError("backend_type must be non-empty")
        if self.tick_hz <= 0:
            raise ValueError("tick_hz must be positive")
        if self.counter_bits <= 0:
            raise ValueError("counter_bits must be positive")


@dataclass(frozen=True)
class PwmMeasurement:
    channel: int
    sequence: int
    period_ticks: int
    high_ticks: int
    low_ticks: int
    valid: bool = True
    overflow: bool = False


@dataclass(frozen=True)
class DioEvent:
    event_id: int
    target_ticks: int
    mask: int
    value: int

    def __post_init__(self) -> None:
        if self.event_id < 0:
            raise ValueError("event_id must be non-negative")
        if self.target_ticks < 0:
            raise ValueError("target_ticks must be non-negative")
        if self.mask < 0 or self.value < 0:
            raise ValueError("mask/value must be non-negative")


class HilBackend(ABC):
    """Backend-neutral control-plane contract.

    Concrete backends keep deterministic timing in FPGA PL or PRU. These
    methods configure or retrieve hardware behavior; they do not permit
    real-time bit banging from Linux.
    """

    @property
    @abstractmethod
    def identity(self) -> BackendIdentity:
        raise NotImplementedError

    def supports(self, capability: Capability) -> bool:
        return capability in self.identity.capabilities

    def require(self, capability: Capability) -> None:
        if not self.supports(capability):
            raise UnsupportedCapability(capability)

    def validate_contract(self) -> None:
        missing = REQUIRED_BACKEND_CAPABILITIES - self.identity.capabilities
        if missing:
            names = ", ".join(sorted(item.value for item in missing))
            raise InvalidConfiguration(f"backend missing required capabilities: {names}")

    @abstractmethod
    def force_safe(self, asserted: bool = True) -> None:
        """Assert backend-local safe state.

        A backend may reject asserted=False when its hardware protocol has no
        explicit deassert operation. Tests must never assume that Linux cleanup
        can release or recreate a hardware-local safety state.
        """

    def read_timestamp(self) -> Timestamp:
        self.require(Capability.TIMEBASE)
        raise NotImplementedError

    @abstractmethod
    def health(self) -> Mapping[str, Any]:
        """Return backend/infrastructure counters, not DUT pass/fail results."""

    def read_pwm(self, channel: int) -> PwmMeasurement:
        self.require(Capability.PWM_CAPTURE)
        raise NotImplementedError

    def configure_abz(self, **config: Any) -> None:
        self.require(Capability.ABZ_GENERATOR)
        raise NotImplementedError

    def start_abz(self) -> None:
        self.require(Capability.ABZ_GENERATOR)
        raise NotImplementedError

    def stop_abz(self) -> None:
        self.require(Capability.ABZ_GENERATOR)
        raise NotImplementedError

    def schedule_dio(self, event: DioEvent) -> None:
        self.require(Capability.DIO_SCHEDULER)
        raise NotImplementedError
