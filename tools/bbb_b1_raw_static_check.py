#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "boards/beaglebone_black"
MAIN = BASE / "firmware/pru0_b1_raw/main.c"
ABI = BASE / "firmware/common/raw_edge_capture.h"
MAKEFILE = BASE / "firmware/pru0_b1_raw/Makefile"
LINKER = BASE / "firmware/pru0_b1_raw/AM335x_PRU_B1_RAW.cmd"
HOST = BASE / "host/hil_raw_shared.py"
CLI = BASE / "host/hil_raw_cli.py"


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def forbid(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is not None:
        errors.append(f"forbidden {label}: /{pattern}/")


def main() -> int:
    errors: list[str] = []
    for path in (MAIN, ABI, MAKEFILE, LINKER, HOST, CLI):
        if not path.is_file():
            errors.append(f"missing {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    main_c = MAIN.read_text(encoding="utf-8")
    abi = ABI.read_text(encoding="utf-8")
    makefile = MAKEFILE.read_text(encoding="utf-8")
    linker = LINKER.read_text(encoding="utf-8")
    host = HOST.read_text(encoding="utf-8")
    cli = CLI.read_text(encoding="utf-8")

    for pattern, label in [
        (r"HIL_RAW_CAPTURE_CAPACITY\s+\(1024u\)", "1024-event raw capacity"),
        (r"struct hil_raw_edge_record", "8-byte raw edge record"),
        (r"timestamp_ticks;", "raw timestamp"),
        (r"raw_inputs;", "raw R31 input state"),
        (r"hil_raw_edge_record_must_be_8_bytes", "8-byte ABI assertion"),
        (r"hil_raw_capture_must_fit_shared_ram", "shared RAM ABI bound"),
    ]:
        require(abi, pattern, label, errors)

    for pattern, label in [
        (r"uint32_t raw_r31 = __R31;", "single R31 loop sample"),
        (r"raw_inputs = raw_r31 & R31_PWM_INPUT_MASK;", "native raw input mask"),
        (r"if \(raw_inputs != last_inputs\)", "raw edge gate"),
        (r"timestamp_ticks = tick_now\(\);", "IEP timestamp"),
        (r"&g_raw_shared\.ring\[event_count\]", "linear raw ring slot"),
        (r"record->timestamp_ticks = timestamp_ticks;", "timestamp store"),
        (r"record->raw_inputs = raw_inputs;", "state store"),
        (r"event_count \+= 1u;", "local event counter"),
        (r"continue;", "immediate return to sampling"),
        (r"HIL_RAW_STOP_EVENT_LIMIT", "bounded auto-stop"),
        (r"start_pending", "post-RPMsg start arm state"),
        (r"baseline_raw = __R31 & R31_PWM_INPUT_MASK", "fresh post-RPMsg R31 baseline"),
        (r"baseline_ticks = tick_now\(\)", "fresh post-RPMsg IEP baseline"),
        (r"g_raw_shared\.running = 1u;", "publish running after fresh baseline"),
        (r"HIL_PRU_B1_RAW_CAPABILITIES", "raw capability handshake"),
        (r"HIL_PRU_B1_RAW_FIRMWARE_VERSION", "raw firmware version"),
    ]:
        require(main_c, pattern, label, errors)

    # Precision path must not call the old semantics-first analyzer.
    forbid(main_c, r"hil_pwm_capture_process", "inline PWM statistics in raw hot path", errors)
    forbid(main_c, r"record_deadtime", "dead-time analysis in raw hot path", errors)
    forbid(main_c, r"for \(channel_", "per-channel loop in raw hot path", errors)
    forbid(main_c, r"for \(pair_", "per-pair loop in raw hot path", errors)
    forbid(
        main_c,
        r"case HIL_PRU_MSG_RAW_START:[\s\S]{0,1200}g_raw_shared\.running = 1u;",
        "entering precise capture inside RAW_START RPMsg handler",
        errors,
    )

    require(linker, r"\.shared_raw\s+>\s+PRU_SHAREDMEM,\s+PAGE 2", "raw shared RAM section", errors)
    require(makefile, r"-O3", "PRU raw optimized build", errors)
    forbid(makefile, r"pwm_capture_core\.object", "legacy capture core in raw firmware", errors)

    for pattern, label in [
        (r"RAW_SHARED_SIZE", "host raw ABI sizing"),
        (r"raw_to_logical", "host R31-to-logical remap"),
        (r"analyze_raw_capture", "offline analyzer"),
        (r"deadtime_high_to_low_ns", "host H->L dead-time reconstruction"),
        (r"deadtime_low_to_high_ns", "host L->H dead-time reconstruction"),
        (r"min_deadtime_violation_count", "host dead-time policy"),
    ]:
        require(host, pattern, label, errors)

    require(cli, r"MSG_RAW_CONFIG", "raw config command", errors)
    require(cli, r"MSG_RAW_START", "raw start command", errors)
    require(cli, r"time\.sleep", "RPMsg-free bounded capture wait", errors)
    require(cli, r"read_frozen_raw_capture", "frozen raw dump", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("BBB B1 raw-edge static checks: PASS")
    print("  hot path: R31 -> changed -> IEP -> 8-byte record -> resample")
    print("  bounded ring: 1024 events")
    print("  analysis: Linux/offline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
