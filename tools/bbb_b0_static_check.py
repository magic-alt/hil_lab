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
INTC_MAP = ROOT / "boards/beaglebone_black/firmware/pru0_b0/intc_map_0.h"
LINKER = ROOT / "boards/beaglebone_black/firmware/pru0_b0/AM335x_PRU.cmd"


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
    intc_map = INTC_MAP.read_text(encoding="utf-8")
    linker = LINKER.read_text(encoding="utf-8")

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
    require(firmware, r'#include "intc_map_0\.h"', "PSSP v6 IRQ-map include", errors)
    require(firmware, r"HOST_INT\s+\(\(uint32_t\)1u << 30\)", "PRU0 host interrupt bit", errors)
    require(firmware, r"TO_ARM_HOST\s+\(16u\)", "PRU0 PRU->ARM system event", errors)
    require(firmware, r"FROM_ARM_HOST\s+\(17u\)", "PRU0 ARM->PRU system event", errors)
    require(firmware, r"pru_rpmsg_init\(", "PSSP RPMsg transport initialization", errors)
    require(firmware, r"CT_INTC\.SICR_bit\.STS_CLR_IDX\s*=\s*FROM_ARM_HOST", "RPMsg event clear", errors)

    require(resource_h, r"#include <pru_virtio_ids\.h>", "virtio RPMsg ID header", errors)
    require(resource_h, r"uint32_t offset\[1\]", "RPMsg-only resource table", errors)
    require(resource_c, r"\.resource_table", "remoteproc resource table section", errors)
    require(resource_c, r"\{\s*1u,\s*1u,", "single resource entry", errors)
    require(resource_c, r"VIRTIO_ID_RPMSG", "RPMsg vdev", errors)
    forbid(resource_h, r"fw_rsc_custom", "legacy custom INTC resource", errors)
    forbid(resource_c, r"fw_rsc_custom_ints|struct ch_map|TYPE_POSTLOAD_VENDOR|TYPE_CUSTOM", "legacy custom INTC data", errors)

    require(intc_map, r'\.pru_irq_map', "PSSP v6 PRU IRQ map section", errors)
    require(intc_map, r"struct pru_irq_rsc\s+hil_b0_irq_rsc", "PRU IRQ resource", errors)
    require(intc_map, r"\{\s*17u,\s*0u,\s*0u\s*\}", "event17 channel0 host0 mapping", errors)
    forbid(intc_map, r"\{\s*16u,", "ARM-target event16 in PRU IRQ map", errors)

    require(linker, r"\.pru_irq_map\s+\(COPY\)", "linker PRU IRQ-map COPY section", errors)

    require(firmware, r"#define IEP_TICK_HZ\s+\(200000000u\)", "IEP tick metadata", errors)
    require(firmware, r"LOOPBACK_OUT_R30_BIT\s+\(0u\)", "P9_31 R30 mapping", errors)
    require(firmware, r"LOOPBACK_IN_R31_BIT\s+\(1u\)", "P9_29 R31 mapping", errors)
    require(firmware, r"WATCHDOG_TICKS", "watchdog", errors)
    require(firmware, r"force_safe\(\)", "safe-state invocation", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("BBB B0 static checks: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
