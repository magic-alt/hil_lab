from __future__ import annotations

from pathlib import Path
import glob
from typing import Any, Callable, Mapping

from ..core import (
    API_VERSION,
    BackendIdentity,
    Capability,
    HilBackend,
    InfrastructureError,
    InvalidConfiguration,
    PwmMeasurement,
    Timestamp,
)

_PWM_VALID_MASK = (1 << 2) | (1 << 3) | (1 << 4)


class BeagleBonePruBackend(HilBackend):
    """Concrete BBB backend over the existing PRU RPMsg/shared-RAM ABI.

    The capture side is PRU0. PRU1 is optional and adds stimulus capabilities.
    Capability discovery is driven by firmware HELLO responses; this class does
    not synthesize missing behavior in Linux.
    """

    def __init__(
        self,
        *,
        capture_rpc: Any,
        stimulus_rpc: Any | None,
        snapshot_reader: Callable[..., Any],
        protocol: Any,
        hardware_revision: str = "beaglebone-black",
        owns_clients: bool = False,
    ) -> None:
        self._capture = capture_rpc
        self._stimulus = stimulus_rpc
        self._snapshot_reader = snapshot_reader
        self._protocol = protocol
        self._owns_clients = owns_clients

        self._capture_hello = self._hello(capture_rpc, "PRU0")
        self._stimulus_hello = (
            self._hello(stimulus_rpc, "PRU1") if stimulus_rpc is not None else None
        )

        tick_hz = self._capture_hello["tick_hz"]
        counter_bits = self._capture_hello["counter_bits"]

        if self._stimulus_hello is not None:
            if (
                self._stimulus_hello["tick_hz"] != tick_hz
                or self._stimulus_hello["counter_bits"] != counter_bits
            ):
                raise InfrastructureError(
                    "PRU0/PRU1 timestamp metadata mismatch; shared-time "
                    "semantics cannot be claimed"
                )

        capabilities = self._map_capabilities(
            self._capture_hello["capabilities_raw"],
            self._stimulus_hello["capabilities_raw"]
            if self._stimulus_hello is not None
            else 0,
        )

        if self._stimulus_hello is not None:
            stim_caps = self._stimulus_hello["capabilities_raw"]
            stimulus_active = any(
                stim_caps & getattr(protocol, name, 0)
                for name in (
                    "CAP_ABZ_EMULATOR",
                    "CAP_HALL_EMULATOR",
                    "CAP_SSI_EMULATOR",
                    "CAP_BISS_EMULATOR",
                    "CAP_SPI_SENSOR_EMULATOR",
                )
            )
            if stimulus_active and not (
                stim_caps & getattr(protocol, "CAP_FORCE_SAFE", 0)
            ):
                raise InfrastructureError(
                    "PRU1 advertises stimulus capability without FORCE_SAFE"
                )

        firmware_parts = [
            f"pru0=0x{self._capture_hello['firmware_version']:08x}"
        ]
        if self._stimulus_hello is not None:
            firmware_parts.append(
                f"pru1=0x{self._stimulus_hello['firmware_version']:08x}"
            )

        self._identity = BackendIdentity(
            backend_type="bbb_pru",
            hardware_revision=hardware_revision,
            firmware_revision=";".join(firmware_parts),
            api_version=API_VERSION,
            capabilities=frozenset(capabilities),
            tick_hz=tick_hz,
            counter_bits=counter_bits,
        )
        self.validate_contract()

    @classmethod
    def open(
        cls,
        *,
        pru0_device: str | None = None,
        pru1_device: str | None = None,
        timeout_ms: int = 1000,
        require_stimulus: bool = False,
        hardware_revision: str = "beaglebone-black",
    ) -> "BeagleBonePruBackend":
        """Open real BBB RPMsg devices and the qualified PRUSS snapshot reader."""

        try:
            from boards.beaglebone_black.host import hil_pru_cli
            from boards.beaglebone_black.host import hil_pru_protocol
            from boards.beaglebone_black.host import hil_pwm_shared
        except Exception as exc:
            raise InfrastructureError(
                f"cannot import BBB runtime modules: {exc}"
            ) from exc

        capture_path = hil_pru_cli.discover_device(pru0_device)
        capture = hil_pru_cli.HilPru(capture_path, timeout_ms)

        stimulus = None
        try:
            stimulus_path = cls._discover_pru1(pru1_device)
            if stimulus_path is not None:
                stimulus = hil_pru_cli.HilPru(stimulus_path, timeout_ms)
            elif require_stimulus:
                raise FileNotFoundError(
                    "PRU1 RPMsg device not found while stimulus is required"
                )

            return cls(
                capture_rpc=capture,
                stimulus_rpc=stimulus,
                snapshot_reader=hil_pwm_shared.read_consistent_snapshot,
                protocol=hil_pru_protocol,
                hardware_revision=hardware_revision,
                owns_clients=True,
            )
        except Exception:
            if stimulus is not None:
                stimulus.close()
            capture.close()
            raise

    @staticmethod
    def _discover_pru1(explicit: str | None) -> str | None:
        if explicit:
            return explicit
        candidates = ["/dev/rpmsg_pru31", "/dev/rpmsg-pru31"]
        candidates.extend(sorted(glob.glob("/dev/rpmsg*31*")))
        for candidate in candidates:
            if Path(candidate).exists():
                return candidate
        return None

    @property
    def identity(self) -> BackendIdentity:
        return self._identity

    def _hello(self, rpc: Any, label: str) -> dict[str, int]:
        try:
            response = rpc.request(self._protocol.MSG_HELLO)
        except Exception as exc:
            raise InfrastructureError(f"{label} HELLO failed: {exc}") from exc

        self._check_response(response, f"{label} HELLO")
        if response.arg1 <= 0 or response.arg2 <= 0:
            raise InfrastructureError(
                f"{label} returned invalid timestamp metadata"
            )
        return {
            "capabilities_raw": int(response.arg0),
            "tick_hz": int(response.arg1),
            "counter_bits": int(response.arg2),
            "firmware_version": int(response.arg3),
        }

    def _check_response(self, response: Any, operation: str) -> None:
        status = int(response.flags)
        if status == 0:
            return
        invalid_mask = getattr(self._protocol, "ERR_INVALID_ARGUMENT", 0)
        if invalid_mask and (status & invalid_mask):
            raise InvalidConfiguration(
                f"{operation} rejected configuration: status=0x{status:08x}"
            )
        raise InfrastructureError(
            f"{operation} failed: status=0x{status:08x}"
        )

    def _request(self, rpc: Any, msg_type: int, operation: str, **kwargs: int) -> Any:
        try:
            response = rpc.request(msg_type, **kwargs)
        except Exception as exc:
            raise InfrastructureError(f"{operation} transport failure: {exc}") from exc
        self._check_response(response, operation)
        return response

    def _map_capabilities(self, pru0_caps: int, pru1_caps: int) -> set[Capability]:
        p = self._protocol
        combined = pru0_caps | pru1_caps
        mapped: set[Capability] = set()

        mapping = (
            ("CAP_TIMEBASE", Capability.TIMEBASE),
            ("CAP_FORCE_SAFE", Capability.FORCE_SAFE),
            ("CAP_PWM_CAPTURE", Capability.PWM_CAPTURE),
            (
                "CAP_PWM_COMPLEMENTARY_MONITOR",
                Capability.PWM_COMPLEMENTARY_MONITOR,
            ),
            ("CAP_ABZ_EMULATOR", Capability.ABZ_GENERATOR),
            ("CAP_SSI_EMULATOR", Capability.SSI_SENSOR_EMULATOR),
            ("CAP_BISS_EMULATOR", Capability.BISS_SENSOR_EMULATOR),
            ("CAP_SPI_SENSOR_EMULATOR", Capability.SPI_SENSOR_EMULATOR),
        )
        for protocol_name, capability in mapping:
            bit = getattr(p, protocol_name, 0)
            if bit and (combined & bit):
                mapped.add(capability)

        # CAP_SCHEDULED_GPIO is intentionally not mapped to DIO_SCHEDULER:
        # the current wire ABI has timestamped ABZ scheduling but no generic
        # masked-DIO enqueue command.
        return mapped

    def read_timestamp(self) -> Timestamp:
        self.require(Capability.TIMEBASE)
        response = self._request(
            self._capture,
            self._protocol.MSG_TIME,
            "PRU0 TIME",
        )
        tick_hz = int(response.arg1)
        counter_bits = int(response.arg2)
        if (
            tick_hz != self.identity.tick_hz
            or counter_bits != self.identity.counter_bits
        ):
            raise InfrastructureError("PRU0 TIME metadata changed after HELLO")
        return Timestamp(
            ticks=int(response.arg0),
            tick_hz=tick_hz,
            counter_bits=counter_bits,
        )

    def force_safe(self, asserted: bool = True) -> None:
        self.require(Capability.FORCE_SAFE)
        if not asserted:
            raise InvalidConfiguration(
                "BBB PRU wire protocol has no generic FORCE_SAFE deassert "
                "command; release stimulus through its explicit configure/start lifecycle"
            )

        clients = [("PRU0", self._capture)]
        if self._stimulus is not None:
            clients.append(("PRU1", self._stimulus))
        for label, client in clients:
            self._request(
                client,
                self._protocol.MSG_FORCE_SAFE,
                f"{label} FORCE_SAFE",
            )

    def health(self) -> Mapping[str, Any]:
        capture_time = self.read_timestamp()
        result: dict[str, Any] = {
            "capture_ticks": capture_time.ticks,
            "tick_hz": capture_time.tick_hz,
            "counter_bits": capture_time.counter_bits,
            "pru0_capabilities_raw": self._capture_hello["capabilities_raw"],
        }

        if self._stimulus is not None:
            response = self._request(
                self._stimulus,
                self._protocol.MSG_TIME,
                "PRU1 TIME",
            )
            result["stimulus_ticks"] = int(response.arg0)
            result["pru1_capabilities_raw"] = self._stimulus_hello[
                "capabilities_raw"
            ]

        if self.supports(Capability.PWM_CAPTURE):
            snapshot = self._read_snapshot()
            result.update(
                {
                    "pwm_running": bool(snapshot.running),
                    "pwm_event_seq": int(snapshot.event_seq),
                    "pwm_fault_flags": int(snapshot.fault_flags),
                }
            )
        return result

    def _read_snapshot(self) -> Any:
        try:
            snapshot = self._snapshot_reader(ring_limit=0)
        except TypeError:
            snapshot = self._snapshot_reader()
        except Exception as exc:
            raise InfrastructureError(f"PRUSS PWM snapshot failed: {exc}") from exc

        if int(snapshot.tick_hz) != self.identity.tick_hz:
            raise InfrastructureError(
                "PRUSS PWM snapshot tick_hz differs from RPMsg HELLO"
            )
        return snapshot

    def read_pwm(self, channel: int) -> PwmMeasurement:
        self.require(Capability.PWM_CAPTURE)
        if not 0 <= channel < 6:
            raise InvalidConfiguration("BBB PWM channel must be 0..5")

        snapshot = self._read_snapshot()
        sample = snapshot.channel[channel]
        flags = int(sample.flags)
        return PwmMeasurement(
            channel=channel,
            sequence=int(snapshot.event_seq),
            period_ticks=int(sample.period_ticks),
            high_ticks=int(sample.high_ticks),
            low_ticks=int(sample.low_ticks),
            valid=(flags & _PWM_VALID_MASK) == _PWM_VALID_MASK,
            overflow=False,
        )

    def _stimulus_rpc(self) -> Any:
        if self._stimulus is None:
            raise InfrastructureError(
                "PRU1 stimulus RPMsg endpoint is not connected"
            )
        return self._stimulus

    def configure_abz(self, **config: Any) -> None:
        self.require(Capability.ABZ_GENERATOR)
        transition_ticks = int(config.get("transition_ticks", 0))
        initial_phase = int(config.get("initial_phase", 0))
        index_interval = int(config.get("index_interval", 0))
        index_width = int(config.get("index_width", 1 if index_interval else 0))
        direction_forward = bool(config.get("direction_forward", True))

        if transition_ticks <= 0:
            raise InvalidConfiguration("transition_ticks must be > 0")
        if not 0 <= initial_phase <= 3:
            raise InvalidConfiguration("initial_phase must be 0..3")
        if index_interval < 0 or index_width < 0:
            raise InvalidConfiguration("index counts must be non-negative")
        if index_interval and index_width > index_interval:
            raise InvalidConfiguration("index_width cannot exceed index_interval")

        flags = (0 if direction_forward else 1) | (initial_phase << 8)
        self._request(
            self._stimulus_rpc(),
            self._protocol.MSG_ABZ_CONFIG,
            "PRU1 ABZ_CONFIG",
            arg0=transition_ticks,
            arg1=index_interval,
            arg2=index_width,
            arg3=flags,
        )

    def start_abz(self) -> None:
        self.require(Capability.ABZ_GENERATOR)
        self._request(
            self._stimulus_rpc(),
            self._protocol.MSG_ABZ_START,
            "PRU1 ABZ_START",
        )

    def stop_abz(self) -> None:
        self.require(Capability.ABZ_GENERATOR)
        self._request(
            self._stimulus_rpc(),
            self._protocol.MSG_ABZ_STOP,
            "PRU1 ABZ_STOP",
        )

    def close(self) -> None:
        if not self._owns_clients:
            return
        if self._stimulus is not None:
            self._stimulus.close()
        self._capture.close()

    def __enter__(self) -> "BeagleBonePruBackend":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        self.close()
