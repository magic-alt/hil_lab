from __future__ import annotations

from dataclasses import dataclass
import socket
import struct
from typing import Any

_CAN_FRAME = struct.Struct("=IB3x8s")


@dataclass(frozen=True)
class CanFrame:
    can_id: int
    data: bytes

    def __post_init__(self) -> None:
        if not 0 <= self.can_id <= 0x7FF:
            raise ValueError("Controller v1 supports classical 11-bit CAN IDs only")
        if len(self.data) > 8:
            raise ValueError("classical CAN payload must be <= 8 bytes")


def pack_can_frame(frame: CanFrame) -> bytes:
    payload = frame.data.ljust(8, b"\x00")
    return _CAN_FRAME.pack(frame.can_id, len(frame.data), payload)


def unpack_can_frame(payload: bytes) -> CanFrame:
    if len(payload) != _CAN_FRAME.size:
        raise ValueError(f"expected {_CAN_FRAME.size} CAN frame bytes")
    can_id, dlc, data = _CAN_FRAME.unpack(payload)
    if dlc > 8:
        raise ValueError(f"invalid classical CAN DLC {dlc}")
    return CanFrame(can_id=can_id & 0x7FF, data=data[:dlc])


class SocketCanBus:
    """Minimal real Linux CAN_RAW transport using the Python standard library."""

    def __init__(self, interface: str, sock: Any) -> None:
        if not interface:
            raise ValueError("interface must be non-empty")
        self.interface = interface
        self._sock = sock

    @classmethod
    def open(cls, interface: str, timeout_s: float | None = None) -> "SocketCanBus":
        af_can = getattr(socket, "AF_CAN", None)
        can_raw = getattr(socket, "CAN_RAW", None)
        if af_can is None or can_raw is None:
            raise RuntimeError("Python/socket platform does not provide SocketCAN")
        sock = socket.socket(af_can, socket.SOCK_RAW, can_raw)
        try:
            sock.bind((interface,))
            if timeout_s is not None:
                if timeout_s <= 0:
                    raise ValueError("timeout_s must be > 0")
                sock.settimeout(timeout_s)
            return cls(interface, sock)
        except Exception:
            sock.close()
            raise

    def send(self, frame: CanFrame) -> None:
        encoded = pack_can_frame(frame)
        written = self._sock.send(encoded)
        if written != len(encoded):
            raise RuntimeError(f"short SocketCAN write {written}/{len(encoded)}")

    def recv(self) -> CanFrame:
        payload = self._sock.recv(_CAN_FRAME.size)
        return unpack_can_frame(payload)

    def close(self) -> None:
        self._sock.close()

    def __enter__(self) -> "SocketCanBus":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
