from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .socketcan import CanFrame


class CanBus(Protocol):
    def send(self, frame: CanFrame) -> None: ...
    def recv(self) -> CanFrame: ...


ABORT_CODES = {
    0x05040000: "SDO protocol timed out",
    0x06010000: "unsupported object access",
    0x06010002: "attempt to write read-only object",
    0x06020000: "object does not exist",
    0x06090011: "subindex does not exist",
    0x06090030: "value range exceeded",
    0x08000000: "general error",
}


class SdoAbort(RuntimeError):
    def __init__(self, code: int, index: int, subindex: int) -> None:
        text = ABORT_CODES.get(code, "unknown SDO abort")
        super().__init__(
            f"SDO abort 0x{code:08x} at 0x{index:04x}:{subindex:02x}: {text}"
        )
        self.code = code
        self.index = index
        self.subindex = subindex


@dataclass(frozen=True)
class SdoUpload:
    index: int
    subindex: int
    data: bytes


class CanopenSdoClient:
    def __init__(self, bus: CanBus, node_id: int, *, max_frames: int = 32) -> None:
        if not 1 <= node_id <= 127:
            raise ValueError("SDO node_id must be 1..127")
        if max_frames <= 0:
            raise ValueError("max_frames must be > 0")
        self.bus = bus
        self.node_id = node_id
        self.max_frames = max_frames

    @property
    def request_cob_id(self) -> int:
        return 0x600 + self.node_id

    @property
    def response_cob_id(self) -> int:
        return 0x580 + self.node_id

    def _response(self, index: int, subindex: int) -> CanFrame:
        for _ in range(self.max_frames):
            frame = self.bus.recv()
            if frame.can_id != self.response_cob_id:
                continue
            if len(frame.data) != 8:
                raise RuntimeError("SDO response must be 8 bytes")
            response_index = frame.data[1] | (frame.data[2] << 8)
            if response_index != index or frame.data[3] != subindex:
                continue
            if frame.data[0] == 0x80:
                code = int.from_bytes(frame.data[4:8], "little")
                raise SdoAbort(code, index, subindex)
            return frame
        raise TimeoutError(
            f"no SDO response for 0x{index:04x}:{subindex:02x} "
            f"within {self.max_frames} received frames"
        )

    def download(self, index: int, subindex: int, data: bytes) -> None:
        commands = {1: 0x2F, 2: 0x2B, 3: 0x27, 4: 0x23}
        try:
            command = commands[len(data)]
        except KeyError as exc:
            raise ValueError("expedited SDO download supports 1..4 bytes") from exc
        payload = bytes((command, index & 0xFF, index >> 8, subindex))
        payload += data.ljust(4, b"\x00")
        self.bus.send(CanFrame(self.request_cob_id, payload))
        response = self._response(index, subindex)
        if response.data[0] != 0x60:
            raise RuntimeError(f"unexpected SDO download response 0x{response.data[0]:02x}")

    def upload(self, index: int, subindex: int) -> SdoUpload:
        payload = bytes((0x40, index & 0xFF, index >> 8, subindex)) + b"\x00" * 4
        self.bus.send(CanFrame(self.request_cob_id, payload))
        response = self._response(index, subindex)
        command = response.data[0]
        if (command & 0xE0) != 0x40 or not (command & 0x02):
            raise RuntimeError("segmented/non-expedited SDO upload is not supported in v1")
        size = 4 - ((command >> 2) & 0x03) if (command & 0x01) else 4
        return SdoUpload(index, subindex, response.data[4:4 + size])

    def download_u8(self, index: int, subindex: int, value: int) -> None:
        self.download(index, subindex, int(value).to_bytes(1, "little", signed=False))

    def download_i8(self, index: int, subindex: int, value: int) -> None:
        self.download(index, subindex, int(value).to_bytes(1, "little", signed=True))

    def download_u16(self, index: int, subindex: int, value: int) -> None:
        self.download(index, subindex, int(value).to_bytes(2, "little", signed=False))

    def download_i16(self, index: int, subindex: int, value: int) -> None:
        self.download(index, subindex, int(value).to_bytes(2, "little", signed=True))

    def download_u32(self, index: int, subindex: int, value: int) -> None:
        self.download(index, subindex, int(value).to_bytes(4, "little", signed=False))

    def download_i32(self, index: int, subindex: int, value: int) -> None:
        self.download(index, subindex, int(value).to_bytes(4, "little", signed=True))

    def upload_u16(self, index: int, subindex: int) -> int:
        data = self.upload(index, subindex).data
        if len(data) != 2:
            raise RuntimeError(f"expected uint16 SDO, got {len(data)} bytes")
        return int.from_bytes(data, "little")
