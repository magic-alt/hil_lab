from __future__ import annotations

from typing import Any, Mapping

from ..core import (
    BackendIdentity,
    Capability,
    DioEvent,
    HilBackend,
    InfrastructureError,
    InvalidConfiguration,
    PwmMeasurement,
    Timestamp,
)


class _ZynqTransportBackend(HilBackend):
    """Semantic adapter around a board-specific PS/AXI/UIO transport.

    A transport must negotiate and return BackendIdentity from the actual
    hardware/bitstream. There is deliberately no in-memory or Linux-GPIO
    fallback for missing hardware transport.
    """

    expected_backend_types: frozenset[str] = frozenset()

    def __init__(self, transport: Any) -> None:
        self._transport = transport
        try:
            identity = transport.read_identity()
        except Exception as exc:
            raise InfrastructureError(
                f"Zynq backend identity handshake failed: {exc}"
            ) from exc

        if not isinstance(identity, BackendIdentity):
            raise InfrastructureError(
                "Zynq transport read_identity() must return BackendIdentity"
            )
        if (
            self.expected_backend_types
            and identity.backend_type not in self.expected_backend_types
        ):
            raise InvalidConfiguration(
                f"transport backend_type {identity.backend_type!r} does not match "
                f"{sorted(self.expected_backend_types)!r}"
            )
        self._identity = identity
        self.validate_contract()

    @property
    def identity(self) -> BackendIdentity:
        return self._identity

    def _call(self, capability: Capability, method: str, *args: Any, **kwargs: Any) -> Any:
        self.require(capability)
        handler = getattr(self._transport, method, None)
        if handler is None:
            raise InfrastructureError(
                f"transport advertises {capability.value} but has no {method}()"
            )
        try:
            return handler(*args, **kwargs)
        except (InvalidConfiguration, InfrastructureError):
            raise
        except Exception as exc:
            raise InfrastructureError(
                f"{self.identity.backend_type} transport {method} failed: {exc}"
            ) from exc

    def read_timestamp(self) -> Timestamp:
        value = self._call(Capability.TIMEBASE, "read_timestamp")
        if not isinstance(value, Timestamp):
            raise InfrastructureError(
                "Zynq transport read_timestamp() must return Timestamp"
            )
        if (
            value.tick_hz != self.identity.tick_hz
            or value.counter_bits != self.identity.counter_bits
        ):
            raise InfrastructureError(
                "Zynq timestamp metadata differs from identity handshake"
            )
        return value

    def force_safe(self, asserted: bool = True) -> None:
        self._call(Capability.FORCE_SAFE, "force_safe", asserted)

    def health(self) -> Mapping[str, Any]:
        handler = getattr(self._transport, "health", None)
        if handler is None:
            raise InfrastructureError("Zynq transport has no health()")
        try:
            result = handler()
        except Exception as exc:
            raise InfrastructureError(f"Zynq transport health failed: {exc}") from exc
        if not isinstance(result, Mapping):
            raise InfrastructureError("Zynq transport health() must return a mapping")
        return result

    def read_pwm(self, channel: int) -> PwmMeasurement:
        value = self._call(Capability.PWM_CAPTURE, "read_pwm", channel)
        if not isinstance(value, PwmMeasurement):
            raise InfrastructureError("Zynq transport read_pwm() returned wrong type")
        return value

    def configure_abz(self, **config: Any) -> None:
        self._call(Capability.ABZ_GENERATOR, "configure_abz", **config)

    def start_abz(self) -> None:
        self._call(Capability.ABZ_GENERATOR, "start_abz")

    def stop_abz(self) -> None:
        self._call(Capability.ABZ_GENERATOR, "stop_abz")

    def schedule_dio(self, event: DioEvent) -> None:
        self._call(Capability.DIO_SCHEDULER, "schedule_dio", event)


class Axu2cgbBackend(_ZynqTransportBackend):
    expected_backend_types = frozenset(
        {"zynq_axu2cgb", "zu2cg_axu2cgb"}
    )


class Ax7010Backend(_ZynqTransportBackend):
    expected_backend_types = frozenset(
        {"zynq7010_ax7010", "zynq_ax7010"}
    )
