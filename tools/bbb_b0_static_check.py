#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
C_HEADER = ROOT / "boards/beaglebone_black/firmware/common/hil_pru_protocol.h"
PY_PROTO = ROOT / "boards/beaglebone_black/host/hil_pru_protocol.py"
MAIN = ROOT / "boards/beaglebone_black/firmware/pru0_b0/main.c"
RESOURCE_C = ROOT / "boards/beaglebone_black/firmware/pru0_b0/resource_table_0.c"
RESOURCE_H = ROOT / "boards/beaglebone_black/firmware/pru0_b0/resource_table_0.h"


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def main() -> int:
    errors: list[str] = []
    c = C_HEADER.read_text(encoding="utf-8")
    py = PY_PROTO.read_text(encoding="utf-8")
    firmware = MAIN.read_text(encoding="utf-8")
    resource_c = RESOURCE_C.read_text(encoding="utf-8")
    resource_h = RESOURCE_H.read_text(encoding="utf-8")

    pairs = [
        (r"HIL_PRU_MAGIC\s+\(0x304C4948u\)", r"MAGIC\s*=\s*0x304C4948", "protocol magic"),
        (r"HIL_PRU_PROTOCOL_VERSION\s+\(1u\)", r"PROTOCOL_VERSION\s*=\s*1", "protocol version"),
        (r"HIL_PRU_MSG_HELLO\s+\(1u\)", r"MSG_HELLO\s*=\s*1", "HELLO id"),
        (r"HIL_PRU_MSG_GPIO_LOOPBACK\s+\(3u\)", r"MSG_GPIO_LOOPBACK\s*=\s*3", "loopback id"),
    ]
    for c_pattern, py_pattern, label in pairs:
        require(c, c_pattern, f"C {label}", errors)
        require(py, py_pattern, f"Python {label}", errors)

    require(firmware, r"#include <sys_mailbox\.h>", "AM335x mailbox header", errors)
    require(firmware, r"MB_FROM_ARM_HOST\s+\(2u\)", "PRU0 ARM->PRU mailbox", errors)
    require(firmware, r"MB_TO_ARM_HOST\s+\(3u\)", "PRU0 PRU->ARM mailbox", errors)
    require(firmware, r"#define IEP_TICK_HZ\s+\(200000000u\)", "IEP tick metadata", errors)
    require(firmware, r"LOOPBACK_OUT_R30_BIT\s+\(0u\)", "P9_31 R30 mapping", errors)
    require(firmware, r"LOOPBACK_IN_R31_BIT\\s+\\(1u\\)", "P9_29 R31 mapping", errors)
    require(firmware, r"WATCHDOG_TICKS", "watchdog", errors)
    require(firmware, r"force_safe\(\)", "safe-state invocation", errors)

    require(resource_c, r"\.resource_table", "remoteproc resource table section", errors)
    require(resource_c, r"VIRTIO_ID_RPMSG", "RPMsg vdev", errors)
    require(resource_h, r"PRU_RPMSG_VQ0_SIZE\s+\(16u\)", "RPMsg vring0 size", errors)
    require(resource_h, r"PRU_RPMSG_VQ1_SIZE\s+\(16u\)", "RPMsg vring1 size", errors)
    require(resource_h, r"RPMSG_PRU_C0_FEATURES", "RPMsg name-service feature", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("BBB B0 static checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
