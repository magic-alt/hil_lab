#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "boards/beaglebone_black"
MAIN = BASE / "firmware/pru1_b2/main.c"
RSC_H = BASE / "firmware/pru1_b2/resource_table_1.h"
RSC_C = BASE / "firmware/pru1_b2/resource_table_1.c"
INTC = BASE / "firmware/pru1_b2/intc_map_1.h"
MAKEFILE = BASE / "firmware/pru1_b2/Makefile"
PINMUX = BASE / "pinmux/setup_b2_abz_outputs.sh"
PRU1_CTL = BASE / "scripts/pru1_ctl.py"
HOST = BASE / "host/hil_stim_cli.py"
ABZ = BASE / "host/hil_abz.py"


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def forbid(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is not None:
        errors.append(f"forbidden {label}: /{pattern}/")


def main() -> int:
    errors: list[str] = []
    for path in (MAIN, RSC_H, RSC_C, INTC, MAKEFILE, PINMUX, PRU1_CTL, HOST, ABZ):
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    main_c = MAIN.read_text(encoding="utf-8")
    rsc_h = RSC_H.read_text(encoding="utf-8")
    rsc_c = RSC_C.read_text(encoding="utf-8")
    intc = INTC.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    pinmux = PINMUX.read_text(encoding="utf-8")
    ctl = PRU1_CTL.read_text(encoding="utf-8")
    host = HOST.read_text(encoding="utf-8")
    abz = ABZ.read_text(encoding="utf-8")

    for pattern, label in [
        (r"HOST_INT\s+\(\(uint32_t\)1u << 31\)", "PRU1 Host1 R31[31]"),
        (r"TO_ARM_HOST\s+\(18u\)", "PRU1 to-ARM event 18"),
        (r"FROM_ARM_HOST\s+\(19u\)", "ARM to PRU1 event 19"),
        (r"CHAN_PORT\s+\(31u\)", "PRU1 RPMsg port 31"),
        (r"ABZ_A_MASK\s+\(1u << 0\)", "A R30[0]"),
        (r"ABZ_B_MASK\s+\(1u << 1\)", "B R30[1]"),
        (r"ABZ_Z_MASK\s+\(1u << 2\)", "Z R30[2]"),
        (r"CT_CFG\.GPCFG1 = 0u;", "PRU1 direct GPO mode"),
        (r"HIL_PRU_B2_CAPABILITIES", "B2 capability handshake"),
        (r"HIL_PRU_B2_FIRMWARE_VERSION", "B2 firmware version"),
        (r"HIL_PRU_MSG_ABZ_CONFIG", "ABZ config command"),
        (r"HIL_PRU_MSG_ABZ_START", "ABZ start command"),
        (r"HIL_PRU_MSG_ABZ_STOP", "ABZ stop command"),
        (r"HIL_PRU_MSG_ABZ_DIRECTION", "ABZ direction command"),
        (r"phase = \(phase \+ 1u\) & 3u;", "forward quadrature step"),
        (r"phase = \(phase \+ 3u\) & 3u;", "reverse quadrature step"),
        (r"force_safe_outputs\(\);", "safe output path"),
        (r"next_transition_ticks = now \+ transition_ticks;", "late resynchronization"),
        (r"late_transition_count \+= 1u;", "late transition counter"),
    ]:
        require(main_c, pattern, label, errors)

    require(main_c, r"case 1u:\s+return ABZ_A_MASK;", "phase 1 = A", errors)
    require(main_c, r"case 2u:\s+return ABZ_A_MASK \| ABZ_B_MASK;", "phase 2 = AB", errors)
    require(main_c, r"case 3u:\s+return ABZ_B_MASK;", "phase 3 = B", errors)

    require(intc, r"\{ 19u, 1u, 1u \}", "event19 -> channel1 -> host1", errors)
    require(rsc_h, r"RPMSG_PRU_C1_FEATURES", "PRU1 RPMsg features", errors)
    require(rsc_c, r"VIRTIO_ID_RPMSG", "PRU1 RPMsg vdev", errors)
    require(makefile, r"hil_b2_pru1\.out", "B2 PRU1 target", errors)
    require(makefile, r"-O3", "optimized PRU1 build", errors)

    for pin, bit in (("P8_45", 0), ("P8_46", 1), ("P8_43", 2)):
        require(pinmux, rf"config-pin {pin} pruout", f"{pin} pruout", errors)
        require(pinmux, rf"{re.escape(pin)} -> PRU1 R30\[{bit}\]", f"{pin} mapping text", errors)

    require(ctl, r'DEFAULT_FIRMWARE_NAME = "am335x-pru1-fw"', "PRU1 firmware name", errors)
    require(ctl, r"4a338000\.pru", "PRU1 remoteproc discovery", errors)
    require(ctl, r"rpmsg_pru31", "PRU1 RPMsg device", errors)

    for pattern, label in [
        (r"transition_ticks_from_rpm", "RPM/PPR abstraction"),
        (r"transition_ticks_from_hz", "transition-rate abstraction"),
        (r"rpm_from_transition_ticks", "rate reporting"),
        (r"encode_config_flags", "direction/phase config encoding"),
    ]:
        require(abz, pattern, label, errors)

    for pattern, label in [
        (r"MSG_ABZ_CONFIG", "host ABZ configure"),
        (r"MSG_ABZ_START", "host ABZ start"),
        (r"MSG_ABZ_STOP", "host ABZ stop"),
        (r"MSG_ABZ_DIRECTION", "host direction reversal"),
        (r"MSG_FORCE_SAFE", "host force-safe"),
        (r"/dev/rpmsg_pru31", "host PRU1 port"),
    ]:
        require(host, pattern, label, errors)

    forbid(main_c, r"while \(.*transition.*\).*__delay_cycles", "busy-delay edge generation", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("BBB B2 PRU1 ABZ static checks: PASS")
    print("  A/B/Z: P8_45/P8_46/P8_43 -> PRU1 R30[0:2]")
    print("  RPMsg: system events 18/19, port 31")
    print("  safe state: A=B=Z=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
