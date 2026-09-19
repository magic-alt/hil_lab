#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "boards/beaglebone_black"
MAIN = BASE / "firmware/pru1_b2_serial/main.c"
MAKEFILE = BASE / "firmware/pru1_b2_serial/Makefile"
SSI_PINMUX = BASE / "pinmux/setup_b2_ssi_biss.sh"
SPI_PINMUX = BASE / "pinmux/setup_b2_spi_sensor.sh"
HOST = BASE / "host/hil_sensor_cli.py"
HELPER = BASE / "host/hil_sensor.py"


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def main() -> int:
    errors: list[str] = []
    for path in (MAIN, MAKEFILE, SSI_PINMUX, SPI_PINMUX, HOST, HELPER):
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    main_c = MAIN.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    ssi_pinmux = SSI_PINMUX.read_text(encoding="utf-8")
    spi_pinmux = SPI_PINMUX.read_text(encoding="utf-8")
    host = HOST.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")

    for pattern, label in [
        (r"SERIAL_MODE_SSI\s+\(1u\)", "SSI mode"),
        (r"SERIAL_MODE_BISS\s+\(2u\)", "BiSS mode"),
        (r"SERIAL_MODE_SPI\s+\(3u\)", "SPI mode"),
        (r"SERIAL_CLK_MASK\s+\(1u << 0\)", "P8_45 clock input"),
        (r"SERIAL_DATA_MASK\s+\(1u << 1\)", "P8_46 data output"),
        (r"SERIAL_CS_MASK\s+\(1u << 2\)", "P8_43 chip-select input"),
        (r"SERIAL_MOSI_MASK\s+\(1u << 3\)", "P8_44 MOSI input"),
        (r"crc6_biss", "BiSS CRC6 implementation"),
        (r"0x03u", "BiSS x^6+x+1 feedback polynomial"),
        (r"HIL_PRU_B2_SERIAL_CAPABILITIES", "serial capability report"),
        (r"HIL_PRU_B2_SERIAL_FIRMWARE_VERSION", "serial firmware version"),
        (r"HIL_PRU_MSG_SERIAL_CONFIG", "serial configure command"),
        (r"HIL_PRU_MSG_SERIAL_DATA", "serial frame/data command"),
        (r"HIL_PRU_MSG_SERIAL_START", "serial start command"),
        (r"HIL_PRU_MSG_SERIAL_STOP", "serial stop command"),
        (r"HIL_PRU_MSG_SERIAL_STATUS", "serial status command"),
        (r"min_half_period_ticks", "measured input clock limit statistic"),
        (r"protocol_error_count", "serial protocol error statistic"),
        (r"force_safe_output", "serial safe-output path"),
    ]:
        require(main_c, pattern, label, errors)

    require(makefile, r"hil_b2_serial_pru1\.out", "serial PRU1 firmware target", errors)
    require(makefile, r"-O3", "optimized serial PRU build", errors)
    require(makefile, r"--stack_size=0x400", "qualified 1 KiB serial PRU1 stack budget", errors)

    for pattern, label in [
        (r"config-pin P8_45 pruin", "SSI/BiSS clock input pinmux"),
        (r"config-pin P8_46 pruout", "SSI/BiSS data output pinmux"),
        (r"RS-422", "SSI/BiSS differential adapter warning"),
    ]:
        require(ssi_pinmux, pattern, label, errors)

    for pattern, label in [
        (r"config-pin P8_45 pruin", "SPI clock input"),
        (r"config-pin P8_46 pruout", "SPI MISO output"),
        (r"config-pin P8_43 pruin", "SPI CS input"),
        (r"config-pin P8_44 pruin", "SPI MOSI input"),
        (r"generic mode-0", "generic SPI compatibility boundary"),
    ]:
        require(spi_pinmux, pattern, label, errors)

    for pattern, label in [
        (r"MSG_SERIAL_CONFIG", "host serial configure"),
        (r"MSG_SERIAL_DATA", "host serial data"),
        (r"MSG_SERIAL_START", "host serial start"),
        (r"MSG_SERIAL_STATUS", "host serial status"),
        (r"measured_clock_ceiling_hz", "host measured serial-clock report"),
    ]:
        require(host, pattern, label, errors)

    require(helper, r"crc6_biss", "host BiSS CRC6 helper", errors)
    require(helper, r"ACK=0, START=1, CDS=0", "host BiSS frame semantics", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("BBB B2 serial-emulator static checks: PASS")
    print("  SSI/BiSS: P8_45 CLK input, P8_46 DATA output")
    print("  SPI mode-0: + P8_43 CS_n input, P8_44 MOSI input")
    print("  limits: hardware clock ceiling remains unqualified until physical tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
