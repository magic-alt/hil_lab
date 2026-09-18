from __future__ import annotations

from dataclasses import dataclass
import struct

MAGIC = 0x304C4948
PROTOCOL_VERSION = 1
FIRMWARE_VERSION = 0x00010000
B1_FIRMWARE_VERSION = 0x00020000

CAP_TIMEBASE = 1 << 0
CAP_RPMSG = 1 << 1
CAP_GPIO_LOOPBACK = 1 << 2
CAP_FORCE_SAFE = 1 << 3
CAP_WATCHDOG = 1 << 4
CAP_PWM_CAPTURE = 1 << 5
CAP_PWM_COMPLEMENTARY_MONITOR = 1 << 6
CAP_SHARED_SNAPSHOT = 1 << 7

MSG_HELLO = 1
MSG_TIME = 2
MSG_GPIO_LOOPBACK = 3
MSG_FORCE_SAFE = 4
MSG_PING = 5
MSG_CAPTURE_CONFIG = 6
MSG_CAPTURE_START = 7
MSG_CAPTURE_STOP = 8
MSG_CAPTURE_CLEAR = 9
MSG_CAPTURE_STATUS = 10
MSG_RESPONSE_BIT = 0x8000

ERR_BAD_LENGTH = 1 << 0
ERR_BAD_MAGIC = 1 << 1
ERR_BAD_VERSION = 1 << 2
ERR_BAD_COMMAND = 1 << 3
ERR_INVALID_ARGUMENT = 1 << 4
ERR_LOOPBACK_NO_RISE = 1 << 5
ERR_LOOPBACK_NO_FALL = 1 << 6
ERR_CAPTURE_RUNNING = 1 << 7

WIRE = struct.Struct("<IHHIIIIII")


@dataclass(frozen=True)
class Message:
    type: int
    seq: int = 0
    flags: int = 0
    arg0: int = 0
    arg1: int = 0
    arg2: int = 0
    arg3: int = 0
    magic: int = MAGIC
    version: int = PROTOCOL_VERSION

    def pack(self) -> bytes:
        return WIRE.pack(
            self.magic,
            self.version,
            self.type,
            self.seq,
            self.flags,
            self.arg0,
            self.arg1,
            self.arg2,
            self.arg3,
        )

    @classmethod
    def unpack(cls, payload: bytes) -> "Message":
        if len(payload) != WIRE.size:
            raise ValueError(f"expected {WIRE.size} bytes, got {len(payload)}")
        magic, version, msg_type, seq, flags, arg0, arg1, arg2, arg3 = WIRE.unpack(payload)
        return cls(
            type=msg_type,
            seq=seq,
            flags=flags,
            arg0=arg0,
            arg1=arg1,
            arg2=arg2,
            arg3=arg3,
            magic=magic,
            version=version,
        )

    def validate_response(self, request_type: int, request_seq: int) -> None:
        if self.magic != MAGIC:
            raise RuntimeError(f"bad response magic 0x{self.magic:08x}")
        if self.version != PROTOCOL_VERSION:
            raise RuntimeError(f"protocol version mismatch: {self.version}")
        expected_type = request_type | MSG_RESPONSE_BIT
        if self.type != expected_type:
            raise RuntimeError(f"response type {self.type:#x}, expected {expected_type:#x}")
        if self.seq != request_seq:
            raise RuntimeError(f"response seq {self.seq}, expected {request_seq}")


def us_to_ticks(us: float, tick_hz: int) -> int:
    if us < 0:
        raise ValueError("microseconds must be non-negative")
    return int(round((us * tick_hz) / 1_000_000.0))


def ticks_to_us(ticks: int, tick_hz: int) -> float:
    if tick_hz <= 0:
        raise ValueError("tick_hz must be positive")
    return (ticks * 1_000_000.0) / tick_hz


def ns_to_ticks(ns: float, tick_hz: int) -> int:
    if ns < 0:
        raise ValueError("nanoseconds must be non-negative")
    return int(round((ns * tick_hz) / 1_000_000_000.0))
