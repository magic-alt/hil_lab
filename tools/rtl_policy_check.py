#!/usr/bin/env python3
"""Small dependency-free policy gate for synthesizable RTL."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl"

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

    sv_files = sorted(RTL.rglob("*.sv")) + sorted(RTL.rglob("*.svh"))
    for path in sv_files:
        errors.append(f"{path.relative_to(ROOT)}: SystemVerilog file extension is not allowed")

    verilog_files = sorted(RTL.rglob("*.v"))
    if not verilog_files:
        errors.append("rtl/: no Verilog source files found")

    for path in verilog_files:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT)

        if "`default_nettype none" not in text:
            errors.append(f"{rel}: missing `default_nettype none")

        if re.search(r"\binitial\b", text):
            errors.append(f"{rel}: synthesizable core must not contain initial blocks")

        for pattern, description in FORBIDDEN.items():
            if re.search(pattern, text):
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
