from __future__ import annotations

SERIAL_MODE_SSI = 1
SERIAL_MODE_BISS = 2
SERIAL_MODE_SPI = 3

SERIAL_FLAG_FAULT_ENABLE = 1 << 0
SERIAL_FLAG_BISS_ERROR_OK = 1 << 1
SERIAL_FLAG_BISS_WARNING_OK = 1 << 2


def crc6_biss(position: int, position_bits: int, error_ok: int = 1, warning_ok: int = 1) -> int:
    if not 1 <= position_bits <= 32:
        raise ValueError("position_bits must be 1..32")
    mask = (1 << position_bits) - 1 if position_bits < 32 else 0xFFFFFFFF
    position &= mask

    crc = 0
    for bit_index in range(position_bits - 1, -1, -1):
        bit = (position >> bit_index) & 1
        feedback = ((crc >> 5) & 1) ^ bit
        crc = (crc << 1) & 0x3F
        if feedback:
            crc ^= 0x03

    status = ((error_ok & 1) << 1) | (warning_ok & 1)
    for bit_index in (1, 0):
        bit = (status >> bit_index) & 1
        feedback = ((crc >> 5) & 1) ^ bit
        crc = (crc << 1) & 0x3F
        if feedback:
            crc ^= 0x03

    return (~crc) & 0x3F


def build_biss_frame(position: int, position_bits: int, error_ok: int = 1, warning_ok: int = 1) -> tuple[int, int]:
    if not 1 <= position_bits <= 32:
        raise ValueError("position_bits must be 1..32")
    mask = (1 << position_bits) - 1 if position_bits < 32 else 0xFFFFFFFF
    position &= mask
    crc = crc6_biss(position, position_bits, error_ok, warning_ok)

    # ACK=0, START=1, CDS=0, position, ERR, WARN, inverted CRC6.
    frame = 0
    frame = (frame << 1) | 0
    frame = (frame << 1) | 1
    frame = (frame << 1) | 0
    frame = (frame << position_bits) | position
    frame = (frame << 1) | (error_ok & 1)
    frame = (frame << 1) | (warning_ok & 1)
    frame = (frame << 6) | crc
    return frame, position_bits + 11


def mode_name(mode: int) -> str:
    return {
        SERIAL_MODE_SSI: "ssi",
        SERIAL_MODE_BISS: "biss",
        SERIAL_MODE_SPI: "spi",
    }.get(mode, f"unknown-{mode}")
