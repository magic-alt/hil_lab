from __future__ import annotations

from dataclasses import dataclass

from .socketcan import CanFrame


@dataclass(frozen=True)
class Emcy:
    node_id: int
    error_code: int
    error_register: int
    manufacturer_data: bytes


def parse_emcy(frame: CanFrame) -> Emcy:
    if not 0x081 <= frame.can_id <= 0x0FF:
        raise ValueError("frame is not a CANopen EMCY")
    if len(frame.data) != 8:
        raise ValueError("EMCY payload must be 8 bytes")
    return Emcy(
        node_id=frame.can_id - 0x80,
        error_code=int.from_bytes(frame.data[0:2], "little"),
        error_register=frame.data[2],
        manufacturer_data=frame.data[3:8],
    )
