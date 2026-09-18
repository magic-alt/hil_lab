#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
XDC = ROOT / "boards" / "zynq7010" / "constraints" / "ax7010_fpga_lite.xdc"
TOP = ROOT / "boards" / "zynq7010" / "rtl" / "ax7010_fpga_lite_top.v"
README = ROOT / "boards" / "zynq7010" / "README.md"

REQUIRED_XDC = [
    "PACKAGE_PIN U18 [get_ports pl_clk_50m]",
    "PACKAGE_PIN W19 [get_ports {dut_pwm_high_in[0]}]",
    "PACKAGE_PIN Y16 [get_ports {dut_pwm_low_in[2]}]",
    "PACKAGE_PIN W15 [get_ports dut_enc_a_in]",
    "PACKAGE_PIN P18 [get_ports dut_ssi_clk_in]",
    "PACKAGE_PIN U15 [get_ports ext_reset_n]",
    "PACKAGE_PIN P16 [get_ports force_safe_in]",
    "PACKAGE_PIN F17 [get_ports {stim_pwm_high_out[0]}]",
    "PACKAGE_PIN G19 [get_ports {stim_pwm_low_out[2]}]",
    "PACKAGE_PIN H18 [get_ports stim_enc_a_out]",
    "PACKAGE_PIN L19 [get_ports stim_ssi_clk_out]",
    "PACKAGE_PIN M20 [get_ports stim_ssi_data_out]",
    "PULLUP   true [get_ports force_safe_in]",
]

REQUIRED_TOP = [
    "module ax7010_fpga_lite_top",
    "pwm_complementary_generator",
    "pwm_capture",
    "pwm_complementary_monitor",
    "abz_encoder_emulator",
    "abz_encoder_capture",
    "ssi_encoder_emulator",
    "ssi_encoder_master_capture",
]

def main() -> int:
    errors = []
    for path in (XDC, TOP, README):
        if not path.exists():
            errors.append(f"missing {path.relative_to(ROOT)}")

    if errors:
        for error in errors:
            print(error)
        return 1

    xdc = XDC.read_text(encoding="utf-8")
    top = TOP.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    for token in REQUIRED_XDC:
        if token not in xdc:
            errors.append(f"XDC missing: {token}")

    for token in REQUIRED_TOP:
        if token not in top:
            errors.append(f"top missing: {token}")

    for token in ("AX7010", "J10", "J11", "3.3 V", "33 ohm", "Zybo"):
        if token not in readme:
            errors.append(f"README missing: {token}")

    if "5 V logic directly" not in readme:
        errors.append("README must state 5 V direct-connection prohibition")

    if errors:
        print("Zynq-7010 static check FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print("Zynq-7010 static check PASSED")
    return 0

if __name__ == "__main__":
    sys.exit(main())
