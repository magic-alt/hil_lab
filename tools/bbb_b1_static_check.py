#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "boards/beaglebone_black/firmware/pru0_b1/main.c"
CORE_H = ROOT / "boards/beaglebone_black/firmware/common/pwm_capture_core.h"
CORE_C = ROOT / "boards/beaglebone_black/firmware/common/pwm_capture_core.c"
LINKER = ROOT / "boards/beaglebone_black/firmware/pru0_b1/AM335x_PRU_B1.cmd"
PINMUX = ROOT / "boards/beaglebone_black/pinmux/setup_b1_pwm_inputs.sh"
HOST_SHARED = ROOT / "boards/beaglebone_black/host/hil_pwm_shared.py"


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def forbid(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is not None:
        errors.append(f"forbidden {label}: /{pattern}/")


def main() -> int:
    errors: list[str] = []
    main_c = MAIN.read_text(encoding="utf-8")
    core_h = CORE_H.read_text(encoding="utf-8")
    core_c = CORE_C.read_text(encoding="utf-8")
    linker = LINKER.read_text(encoding="utf-8")
    pinmux = PINMUX.read_text(encoding="utf-8")
    host_shared = HOST_SHARED.read_text(encoding="utf-8")

    # Fixed first-board PRU0 direct-input map.
    for pattern, label in [
        (r"R31_UH_MASK\s+\(1u << 1\)", "UH R31[1]"),
        (r"R31_UL_MASK\s+\(1u << 2\)", "UL R31[2]"),
        (r"R31_VH_MASK\s+\(1u << 3\)", "VH R31[3]"),
        (r"R31_VL_MASK\s+\(1u << 5\)", "VL R31[5]"),
        (r"R31_WH_MASK\s+\(1u << 14\)", "WH R31[14]"),
        (r"R31_WL_MASK\s+\(1u << 15\)", "WL R31[15]"),
    ]:
        require(main_c, pattern, label, errors)

    require(main_c, r"uint32_t raw_r31 = __R31;", "single R31 loop sample", errors)
    require(main_c, r"logical_inputs != last_inputs", "edge-change gate", errors)
    require(main_c, r"timestamp_ticks = tick_now\(\)", "IEP timestamp on change", errors)
    require(main_c, r"hil_pwm_capture_process", "capture-core invocation", errors)
    require(main_c, r"HIL_PRU_B1_CAPABILITIES", "B1 capability handshake", errors)
    require(main_c, r'HIL_PRU_MSG_CAPTURE_CONFIG', "capture control command", errors)

    require(core_h, r"HIL_PWM_RING_CAPACITY\s+\(128u\)", "128-entry edge ring", errors)
    require(core_h, r"struct hil_pwm_shared", "shared snapshot ABI", errors)
    require(core_h, r"struct hil_pwm_channel_snapshot", "channel snapshot", errors)
    require(core_h, r"struct hil_pwm_pair_snapshot", "pair snapshot", errors)
    require(core_c, r"period_ticks = timestamp_ticks - channel->last_rise_ticks", "period measurement", errors)
    require(core_c, r"high_ticks = timestamp_ticks - channel->last_rise_ticks", "high-time measurement", errors)
    require(core_c, r"low_ticks = timestamp_ticks - channel->last_fall_ticks", "low-time measurement", errors)
    require(core_c, r"record_deadtime", "dead-time measurement", errors)
    require(core_c, r"HIL_PWM_FAULT_OVERLAP", "overlap latch", errors)
    require(core_c, r"HIL_PWM_FAULT_DEADTIME", "dead-time violation latch", errors)
    forbid(core_c, r"pru_rpmsg_", "RPMsg in deterministic capture core", errors)

    require(linker, r"\.shared_pwm\s+>\s+PRU_SHAREDMEM,\s+PAGE 2", "shared-RAM linker section", errors)
    require(host_shared, r"PRUSS_SHARED_PHYS_BASE\s*=\s*0x4A310000", "AM335x shared-RAM physical base", errors)
    require(host_shared, r"PWM_SHARED_SIZE\s*=\s*ctypes\.sizeof\(PwmShared\)", "host ABI sizing", errors)

    for pin in ("P9_29", "P9_30", "P9_28", "P9_27", "P8_16", "P8_15"):
        require(pinmux, rf"config-pin {pin} pruin", f"{pin} pruin pinmux", errors)
    forbid(pinmux, r"P9_25", "P9_25 in B1 PWM input map", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("BBB B1 static checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
