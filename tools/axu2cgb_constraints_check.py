#!/usr/bin/env python3
"""Static integrity gate for the ALINX AXU2CGB HIL pin map."""

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
XDC = ROOT / "boards" / "zu2cg" / "constraints" / "axu2cgb_hil.xdc"

EXPECTED = {
    "pl_ref_clk": "AB11",
    "pwm_high_in[0]": "F7", "pwm_low_in[0]": "G8",
    "pwm_high_in[1]": "F6", "pwm_low_in[1]": "G6",
    "pwm_high_in[2]": "D9", "pwm_low_in[2]": "E9",
    "spi_sclk_in": "F5", "spi_cs_n_in": "G5", "spi_mosi_in": "E8",
    "ext_reset_n": "F8", "hil_enable_in": "D5",
    "encoder_direction_in": "E5", "clear_faults_in": "C4",
    "force_safe_in": "D4", "test_pattern_enable_in": "E3",
    "dac_pattern_select_in[0]": "E4", "dac_pattern_select_in[1]": "F1",
    "enc_a_out": "A11", "enc_b_out": "A12", "enc_z_out": "A13",
    "spi_miso_out": "B13",
    "dio_out[0]": "A14", "dio_out[1]": "B14",
    "dio_out[2]": "E13", "dio_out[3]": "E14",
    "dio_out[4]": "A15", "dio_out[5]": "B15",
    "dio_out[6]": "C13", "dio_out[7]": "C14",
    "dio_out[8]": "B10", "dio_out[9]": "C11",
    "dio_out[10]": "D14", "dio_out[11]": "D15",
    "dio_out[12]": "F11", "dio_out[13]": "F12",
    "dio_out[14]": "H13", "dio_out[15]": "H14",
    "status_out[0]": "G14", "status_out[1]": "G15",
    "status_out[2]": "F10", "status_out[3]": "G11",
    "dac_sclk_out": "H12", "dac_cs_n_out": "J12",
    "dac_mosi_a_out": "J14", "dac_mosi_b_out": "K14",
    "dac_reset_n_out": "K12", "dac_ldac_n_out": "K13",
    "dac_output_enable_out": "L13", "dac_initialized_out": "L14",
    "dac_stream_active_out": "G10",
    "led_n[0]": "W13", "led_n[1]": "Y12",
    "led_n[2]": "AA12", "led_n[3]": "AB13",
}

PIN_RE = re.compile(
    r"^\s*set_property\s+PACKAGE_PIN\s+(\S+)\s+\[get_ports\s+(?:\{([^}]+)\}|([^\]]+))\]"
)


def main() -> int:
    text = XDC.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    pins: dict[str, str] = {}
    errors: list[str] = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        match = PIN_RE.match(line)
        if not match:
            continue
        pin, braced_port, plain_port = match.groups()
        port = (braced_port or plain_port).strip()
        if port in found:
            errors.append(f"line {line_number}: duplicate constraint for port {port}")
        if pin in pins:
            errors.append(
                f"line {line_number}: package pin {pin} reused by {port} and {pins[pin]}"
            )
        found[port] = pin
        pins[pin] = port

    for port, expected_pin in EXPECTED.items():
        actual_pin = found.get(port)
        if actual_pin != expected_pin:
            errors.append(
                f"{port}: expected PACKAGE_PIN {expected_pin}, got {actual_pin or 'missing'}"
            )

    unexpected = sorted(set(found) - set(EXPECTED))
    if unexpected:
        errors.append(f"unexpected PACKAGE_PIN ports: {', '.join(unexpected)}")

    if not re.search(r"create_clock\s+-period\s+40\.000\b", text):
        errors.append("PL reference clock must remain constrained to 25 MHz (40.000 ns)")

    if "set_property IOSTANDARD LVCMOS33 [get_ports pl_ref_clk]" not in text:
        errors.append("pl_ref_clk must match the ALINX factory XDC LVCMOS33 constraint")

    for safe_rule in (
        "set_property PULLDOWN true [get_ports hil_enable_in]",
        "set_property PULLUP   true [get_ports force_safe_in]",
        "set_property PULLUP   true [get_ports spi_cs_n_in]",
        "set_property PULLDOWN true [get_ports {dac_pattern_select_in[*]}]",
    ):
        if safe_rule not in text:
            errors.append(f"missing fail-safe XDC rule: {safe_rule}")

    if errors:
        print("AXU2CGB constraint check FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"AXU2CGB constraint check PASSED ({len(found)} package pins)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
