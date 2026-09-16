#!/usr/bin/env python3
"""Small dependency-free policy gate for synthesizable Verilog RTL."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RTL_ROOTS = [
    ROOT / "rtl",
    ROOT / "boards" / "zu2cg" / "rtl",
]

FORBIDDEN = {
    r"\balways_ff\b": "SystemVerilog always_ff",
    r"\balways_comb\b": "SystemVerilog always_comb",
    r"\balways_latch\b": "SystemVerilog always_latch",
    r"\btypedef\b": "SystemVerilog typedef",
    r"\binterface\b": "SystemVerilog interface",
    r"\bpackage\b": "SystemVerilog package",
    r"\bendmodule\s*:\s*": "named endmodule syntax",
}


def main() -> int:
    errors = []
    verilog_files = []

    for rtl_root in RTL_ROOTS:
        if not rtl_root.exists():
            continue

        sv_files = sorted(rtl_root.rglob("*.sv")) + sorted(rtl_root.rglob("*.svh"))
        for path in sv_files:
            errors.append(f"{path.relative_to(ROOT)}: SystemVerilog file extension is not allowed")

        verilog_files.extend(sorted(rtl_root.rglob("*.v")))

    if not verilog_files:
        errors.append("no synthesizable Verilog source files found")

    for path in verilog_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)
        code = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        code = re.sub(r"//.*", "", code)

        if "`default_nettype none" not in text:
            errors.append(f"{rel}: missing `default_nettype none")

        if re.search(r"\binitial\b", code):
            errors.append(f"{rel}: synthesizable core must not contain initial blocks")

        for pattern, description in FORBIDDEN.items():
            if re.search(pattern, code):
                errors.append(f"{rel}: forbidden construct: {description}")

    if errors:
        print("RTL policy check FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"RTL policy check PASSED ({len(verilog_files)} Verilog files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
