from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .sdo import CanopenSdoClient
from .socketcan import CanFrame


@dataclass(frozen=True)
class PdoMappingEntry:
    name: str
    index: int
    subindex: int
    bits: int
    signed: bool = False

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PDO entry name must be non-empty")
        if not 0 <= self.index <= 0xFFFF:
            raise ValueError("PDO index must fit uint16")
        if not 0 <= self.subindex <= 0xFF:
            raise ValueError("PDO subindex must fit uint8")
        if self.bits not in (8, 16, 32):
            raise ValueError("PDO v1 supports byte-aligned 8/16/32-bit entries")

    @property
    def mapping_value(self) -> int:
        return (self.index << 16) | (self.subindex << 8) | self.bits


@dataclass(frozen=True)
class PdoMapping:
    cob_id: int
    entries: tuple[PdoMappingEntry, ...]

    def __post_init__(self) -> None:
        if not 0 <= self.cob_id <= 0x7FF:
            raise ValueError("PDO v1 supports standard 11-bit COB-IDs")
        if not 1 <= len(self.entries) <= 8:
            raise ValueError("PDO must contain 1..8 mapped entries")
        if sum(entry.bits for entry in self.entries) > 64:
            raise ValueError("classic CAN PDO payload cannot exceed 64 bits")

    @property
    def payload_bytes(self) -> int:
        return sum(entry.bits for entry in self.entries) // 8

    def encode(self, values: Mapping[str, int]) -> CanFrame:
        payload = bytearray()
        for entry in self.entries:
            if entry.name not in values:
                raise KeyError(entry.name)
            width = entry.bits // 8
            payload.extend(
                int(values[entry.name]).to_bytes(
                    width, "little", signed=entry.signed
                )
            )
        return CanFrame(self.cob_id, bytes(payload))

    def decode(self, frame: CanFrame) -> dict[str, int]:
        if frame.can_id != self.cob_id:
            raise ValueError(
                f"PDO COB-ID 0x{frame.can_id:03x}, expected 0x{self.cob_id:03x}"
            )
        if len(frame.data) != self.payload_bytes:
            raise ValueError(
                f"PDO payload {len(frame.data)} bytes, expected {self.payload_bytes}"
            )
        result: dict[str, int] = {}
        offset = 0
        for entry in self.entries:
            width = entry.bits // 8
            result[entry.name] = int.from_bytes(
                frame.data[offset:offset + width],
                "little",
                signed=entry.signed,
            )
            offset += width
        return result


def configure_pdo_mapping(
    sdo: CanopenSdoClient,
    *,
    mapping_index: int,
    communication_index: int,
    mapping: PdoMapping,
    transmission_type: int | None = None,
) -> None:
    """Configure one RPDO/TPDO mapping using the standard CANopen sequence.

    The PDO is disabled through bit31 of the communication COB-ID, the mapping
    count is cleared, each mapping entry is written, the count is restored,
    optional transmission type is configured, then the PDO is re-enabled.
    """

    if not 0x1400 <= communication_index <= 0x19FF:
        raise ValueError("communication_index must be a PDO communication object")
    if not 0x1600 <= mapping_index <= 0x1BFF:
        raise ValueError("mapping_index must be a PDO mapping object")
    if transmission_type is not None and not 0 <= transmission_type <= 0xFF:
        raise ValueError("transmission_type must fit uint8")

    disabled_cob_id = mapping.cob_id | 0x80000000
    sdo.download_u32(communication_index, 1, disabled_cob_id)
    sdo.download_u8(mapping_index, 0, 0)

    for subindex, entry in enumerate(mapping.entries, start=1):
        sdo.download_u32(mapping_index, subindex, entry.mapping_value)

    sdo.download_u8(mapping_index, 0, len(mapping.entries))
    if transmission_type is not None:
        sdo.download_u8(communication_index, 2, transmission_type)
    sdo.download_u32(communication_index, 1, mapping.cob_id)


CIA402_RPDO = PdoMapping(
    cob_id=0x200,
    entries=(
        PdoMappingEntry("controlword", 0x6040, 0, 16),
        PdoMappingEntry("mode", 0x6060, 0, 8, signed=True),
        PdoMappingEntry("target_torque", 0x6071, 0, 16, signed=True),
        PdoMappingEntry("target_velocity", 0x60FF, 0, 32, signed=True),
    ),
)

CIA402_TPDO = PdoMapping(
    cob_id=0x180,
    entries=(
        PdoMappingEntry("statusword", 0x6041, 0, 16),
        PdoMappingEntry("mode_display", 0x6061, 0, 8, signed=True),
        PdoMappingEntry("torque_actual", 0x6077, 0, 16, signed=True),
        PdoMappingEntry("velocity_actual", 0x606C, 0, 32, signed=True),
    ),
)


def with_node_id(mapping: PdoMapping, node_id: int) -> PdoMapping:
    if not 1 <= node_id <= 127:
        raise ValueError("node_id must be 1..127")
    return PdoMapping(mapping.cob_id + node_id, mapping.entries)
