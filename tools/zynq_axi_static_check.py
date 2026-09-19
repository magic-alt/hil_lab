#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

FILES = {
    "rtl": ROOT / "rtl" / "control" / "hil_axi_control_plane.v",
    "py": ROOT / "host" / "hil" / "transports" / "register_map.py",
    "ax_dts": ROOT / "boards" / "zynq7010" / "linux" / "hil-uio.dtsi",
    "zu_dts": ROOT / "boards" / "zu2cg" / "linux" / "hil-uio.dtsi",
}

TOKENS = {
    "rtl": ["32'h48494C32", "12'h114", "12'h118", "ram_style"],
    "py": ["MAGIC = 0x48494C32", "REG_EVT_PUSH = 0x114", "REG_EVT_STATUS = 0x118"],
    "ax_dts": ["0x43c00000", "0x1000", "generic-uio"],
    "zu_dts": ["0xa0000000", "0x1000", "generic-uio"],
}

def main() -> int:
    errors = []
    for name, path in FILES.items():
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        for token in TOKENS[name]:
            if token not in text:
                errors.append(f"{path.relative_to(ROOT)} missing {token}")
    if errors:
        print("Zynq AXI static check FAILED")
        for error in errors:
            print(f" - {error}")
        return 1
    print("Zynq AXI static check PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
