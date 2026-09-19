from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .nmt import NmtCommand, build_nmt_frame
from .sdo import CanopenSdoClient


class CiA402State(str, Enum):
    NOT_READY = "not_ready"
    SWITCH_ON_DISABLED = "switch_on_disabled"
    READY_TO_SWITCH_ON = "ready_to_switch_on"
    SWITCHED_ON = "switched_on"
    OPERATION_ENABLED = "operation_enabled"
    QUICK_STOP_ACTIVE = "quick_stop_active"
    FAULT_REACTION_ACTIVE = "fault_reaction_active"
    FAULT = "fault"
    UNKNOWN = "unknown"


def decode_state(statusword: int) -> CiA402State:
    if (statusword & 0x004F) == 0x0000:
        return CiA402State.NOT_READY
    if (statusword & 0x004F) == 0x0040:
        return CiA402State.SWITCH_ON_DISABLED
    if (statusword & 0x006F) == 0x0021:
        return CiA402State.READY_TO_SWITCH_ON
    if (statusword & 0x006F) == 0x0023:
        return CiA402State.SWITCHED_ON
    if (statusword & 0x006F) == 0x0027:
        return CiA402State.OPERATION_ENABLED
    if (statusword & 0x006F) == 0x0007:
        return CiA402State.QUICK_STOP_ACTIVE
    if (statusword & 0x004F) == 0x000F:
        return CiA402State.FAULT_REACTION_ACTIVE
    if (statusword & 0x004F) == 0x0008:
        return CiA402State.FAULT
    return CiA402State.UNKNOWN


def next_controlword(statusword: int) -> int:
    state = decode_state(statusword)
    if state is CiA402State.FAULT:
        return 0x0080
    if state is CiA402State.SWITCH_ON_DISABLED:
        return 0x0006
    if state is CiA402State.READY_TO_SWITCH_ON:
        return 0x0007
    if state in (CiA402State.SWITCHED_ON, CiA402State.OPERATION_ENABLED):
        return 0x000F
    if state is CiA402State.QUICK_STOP_ACTIVE:
        return 0x000F
    return 0x0000


@dataclass
class CanopenCiA402Node:
    bus: object
    node_id: int
    sdo: CanopenSdoClient

    @classmethod
    def create(cls, bus, node_id: int) -> "CanopenCiA402Node":
        return cls(bus=bus, node_id=node_id, sdo=CanopenSdoClient(bus, node_id))

    def set_mode(self, mode: int) -> None:
        if mode not in (1, 3, 4, 6, 8, 9, 10):
            raise ValueError("unsupported/unknown CiA402 mode")
        self.sdo.download_i8(0x6060, 0, mode)

    def start_nmt(self) -> None:
        self.bus.send(build_nmt_frame(NmtCommand.START_REMOTE_NODE, self.node_id))

    def statusword(self) -> int:
        return self.sdo.upload_u16(0x6041, 0)

    def enable_operation(self, mode: int, *, max_steps: int = 16) -> CiA402State:
        if max_steps <= 0:
            raise ValueError("max_steps must be > 0")
        self.set_mode(mode)
        self.start_nmt()
        for _ in range(max_steps):
            sw = self.statusword()
            state = decode_state(sw)
            if state is CiA402State.OPERATION_ENABLED:
                return state
            self.sdo.download_u16(0x6040, 0, next_controlword(sw))
        raise RuntimeError("CiA402 did not reach Operation Enabled")

    def quick_stop(self) -> None:
        self.sdo.download_u16(0x6040, 0, 0x000B)

    def disable_voltage(self) -> None:
        self.sdo.download_u16(0x6040, 0, 0x0000)
