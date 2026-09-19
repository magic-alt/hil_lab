from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum

from .socketcan import CanFrame


class NmtCommand(IntEnum):
    START_REMOTE_NODE = 0x01
    STOP_REMOTE_NODE = 0x02
    ENTER_PRE_OPERATIONAL = 0x80
    RESET_NODE = 0x81
    RESET_COMMUNICATION = 0x82


class NmtState(IntEnum):
    BOOTUP = 0x00
    STOPPED = 0x04
    OPERATIONAL = 0x05
    PRE_OPERATIONAL = 0x7F


@dataclass(frozen=True)
class Heartbeat:
    node_id: int
    state: NmtState


def build_nmt_frame(command: NmtCommand, node_id: int) -> CanFrame:
    if not 0 <= node_id <= 127:
        raise ValueError("NMT node_id must be 0..127")
    return CanFrame(can_id=0x000, data=bytes((int(command), node_id)))


def parse_heartbeat(frame: CanFrame) -> Heartbeat:
    if not 0x701 <= frame.can_id <= 0x77F:
        raise ValueError("frame is not a CANopen heartbeat/boot-up frame")
    if len(frame.data) != 1:
        raise ValueError("heartbeat payload must be exactly one byte")
    node_id = frame.can_id - 0x700
    try:
        state = NmtState(frame.data[0])
    except ValueError as exc:
        raise ValueError(f"unknown CANopen NMT state 0x{frame.data[0]:02x}") from exc
    return Heartbeat(node_id=node_id, state=state)


def wait_for_heartbeat(bus, node_id: int, *, max_frames: int = 64) -> Heartbeat:
    if not 1 <= node_id <= 127:
        raise ValueError("heartbeat node_id must be 1..127")
    for _ in range(max_frames):
        frame = bus.recv()
        if frame.can_id == 0x700 + node_id:
            return parse_heartbeat(frame)
    raise TimeoutError(f"heartbeat from node {node_id} not observed")
