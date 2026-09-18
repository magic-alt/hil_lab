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


def forbid(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is not None:
        errors.append(f"forbidden {label}: /{pattern}/")


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

    require(firmware, r"#include <pru_intc\.h>", "AM335x PRU INTC header", errors)
    require(firmware, r"HOST_INT\s+\(\(uint32_t\)1u << 30\)", "PRU0 host interrupt bit", errors)
    require(firmware, r"TO_ARM_HOST\s+\(16u\)", "PRU0 PRU->ARM system event", errors)
    require(firmware, r"FROM_ARM_HOST\s+\(17u\)", "PRU0 ARM->PRU system event", errors)
    require(firmware, r"pru_rpmsg_init\(", "PSSP RPMsg transport initialization", errors)
    require(firmware, r"CT_INTC\.SICR_bit\.STS_CLR_IDX\s*=\s*FROM_ARM_HOST", "RPMsg event clear", errors)
    forbid(firmware, r"pru_virtqueue_init\(", "direct virtqueue init", errors)
    forbid(firmware, r"CT_MBX\.MESSAGE", "legacy mailbox polling path", errors)

    require(firmware, r"#define IEP_TICK_HZ\s+\(200000000u\)", "IEP tick metadata", errors)
    require(firmware, r"LOOPBACK_OUT_R30_BIT\s+\(0u\)", "P9_31 R30 mapping", errors)
    require(firmware, r"LOOPBACK_IN_R31_BIT\s+\(1u\)", "P9_29 R31 mapping", errors)
    require(firmware, r"WATCHDOG_TICKS", "watchdog", errors)
    require(firmware, r"force_safe\(\)", "safe-state invocation", errors)

    require(resource_h, r"#include <pru_virtio_ids\.h>", "virtio RPMsg ID header", errors)
    require(resource_h, r"uint32_t offset\[2\]", "two-entry resource table", errors)
    require(resource_h, r"struct fw_rsc_custom pru_ints", "PRU INTC custom resource", errors)
    require(resource_c, r"\.resource_table", "remoteproc resource table section", errors)
    require(resource_c, r"VIRTIO_ID_RPMSG", "RPMsg vdev", errors)
    require(resource_c, r"\{\s*16u,\s*2u\s*\}", "system event 16 mapping", errors)
    require(resource_c, r"\{\s*17u,\s*0u\s*\}", "system event 17 mapping", errors)
    require(resource_c, r"TYPE_CUSTOM,\s*TYPE_PRU_INTS", "PRU INTC resource type", errors)
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
