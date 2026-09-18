#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

PROFILES = {
    "20k_50_600ns": (500, 600, 1),
    "20k_50_700ns": (500, 700, 2),
    "20k_50_800ns": (500, 800, 3),
    "20k_5_700ns": (50, 700, 4),
    "20k_25_700ns": (250, 700, 5),
    "20k_75_700ns": (750, 700, 6),
    "20k_95_700ns": (950, 700, 7),
}

HPM = ROOT / "boards/hpm6e00evk"
GD = ROOT / "boards/gd32h75ey_eval"
STM_PROJECT = ROOT / "boards/stm32f429i_disc1/MDK-ARM/hil_pwm_stimulus.uvprojx"


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def parse_defines(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in raw.split(","):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key.strip()] = value.strip()
        elif item.strip():
            result[item.strip()] = ""
    return result


def dtg_encode(deadtime_ns: int, timer_hz: int) -> int:
    ticks = (deadtime_ns * timer_hz + 500_000_000) // 1_000_000_000
    if ticks <= 127:
        return ticks
    if ticks <= 254:
        scaled = max(64, min(127, (ticks + 1) // 2))
        return 0x80 | (scaled - 64)
    if ticks <= 504:
        scaled = max(32, min(63, (ticks + 4) // 8))
        return 0xC0 | (scaled - 32)
    scaled = max(32, min(63, (ticks + 8) // 16))
    return 0xE0 | (scaled - 32)


def check_common_profiles(errors: list[str]) -> None:
    root = ET.parse(STM_PROJECT).getroot()
    stm_names = {
        node.findtext("TargetName", default="")
        for node in root.findall("./Targets/Target")
    }
    if stm_names != set(PROFILES):
        errors.append(f"STM32 profile set differs from common set: {sorted(stm_names)}")


def check_hpm(errors: list[str]) -> None:
    required = [
        HPM / "CMakeLists.txt",
        HPM / "app.yaml",
        HPM / "inc/pwm_profile.h",
        HPM / "src/main.c",
        HPM / "build_all.ps1",
        HPM / "README.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing HPM6E file: {path.relative_to(ROOT)}")
    if errors:
        return

    cmake = (HPM / "CMakeLists.txt").read_text(encoding="utf-8")
    app = (HPM / "app.yaml").read_text(encoding="utf-8")
    source = (HPM / "src/main.c").read_text(encoding="utf-8")
    build = (HPM / "build_all.ps1").read_text(encoding="utf-8")
    readme = (HPM / "README.md").read_text(encoding="utf-8")

    require(cmake, r'find_package\(hpm-sdk REQUIRED HINTS \$ENV\{HPM_SDK_BASE\}\)',
            "HPM SDK discovery", errors)
    require(cmake, r'BOARD=hpm6e00evk|HIL_PWM_PROFILE',
            "HPM profile build contract", errors)
    require(app, r'pwmv2', "HPM PWMV2 dependency", errors)

    for name in PROFILES:
        require(cmake, re.escape(name), f"HPM CMake profile {name}", errors)
        require(build, re.escape(name), f"HPM batch profile {name}", errors)

    for pattern, label in [
        (r'#define PWM_BASE BOARD_APP_PWM', "BOARD_APP_PWM use"),
        (r'clock_get_frequency\(PWM_CLOCK_NAME\)', "runtime PWM clock"),
        (r'pwmv2_setup_waveform_in_pair', "PWMV2 pair setup"),
        (r'pwm_channel_0', "U pair channel 0"),
        (r'pwm_channel_2', "V pair channel 2"),
        (r'pwm_channel_4', "W pair channel 4"),
        (r'dead_zone_in_half_cycle = dead_ticks', "PWMV2 dead-zone programming"),
        (r'pwmv2_enable_multi_counter_sync\(PWM_BASE, 0x07U\)', "three-counter sync"),
        (r'pwmv2_start_pwm_output_sync\(PWM_BASE, 0x07U\)', "synchronized PWM start"),
        (r'init_pwm_pins\(PWM_BASE\)', "HPM board pinmux"),
    ]:
        require(source, pattern, label, errors)

    for pin in ("PE08", "PE09", "PE10", "PE11", "PE12", "PE13"):
        require(readme, pin, f"HPM pin {pin}", errors)

    for bbb in ("P9_29", "P9_30", "P9_28", "P9_27", "P8_16", "P8_15"):
        require(readme, bbb, f"HPM BBB destination {bbb}", errors)


def check_gd32(errors: list[str]) -> None:
    project = GD / "MDK-ARM/hil_pwm_stimulus.uvprojx"
    required = [
        project,
        GD / "MDK-ARM/build_all.bat",
        GD / "Inc/pwm_profile.h",
        GD / "Inc/gd32h75e_libopt.h",
        GD / "Src/main.c",
        GD / "prepare_vendor.ps1",
        GD / "Vendor/README.md",
        GD / "README.md",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing GD32H75E file: {path.relative_to(ROOT)}")
    if any(not path.is_file() for path in required):
        return

    source = (GD / "Src/main.c").read_text(encoding="utf-8")
    prep = (GD / "prepare_vendor.ps1").read_text(encoding="utf-8")
    build = (GD / "MDK-ARM/build_all.bat").read_text(encoding="utf-8")
    readme = (GD / "README.md").read_text(encoding="utf-8")

    for pattern, label in [
        (r'RCU_TIMER_PSC_MUL4', "TIMER clock MUL4 selection"),
        (r'rcu_clock_freq_get\(CK_AHB\)', "AHB clock query"),
        (r'rcu_clock_freq_get\(CK_APB2\)', "APB2 clock query"),
        (r'gd32_timer_init\(TIMER0', "TIMER0 init"),
        (r'TIMER_CH_0', "TIMER0 CH0"),
        (r'TIMER_CH_1', "TIMER0 CH1"),
        (r'TIMER_CH_2', "TIMER0 CH2"),
        (r'TIMER_CCXN_ENABLE', "complementary outputs"),
        (r'timer_break_config\(TIMER0', "dead-time/break config"),
        (r'timer_primary_output_config\(TIMER0, ENABLE\)', "TIMER0 primary output enable"),
        (r'GPIO_AF_1', "TIMER0 AF1"),
        (r'GPIO_PIN_8 \| GPIO_PIN_7', "PA8/PA7 U pair"),
        (r'GPIO_PIN_11', "PE11 V high"),
        (r'GPIO_PIN_0', "PB0 V low"),
        (r'GPIO_PIN_13 \| GPIO_PIN_12', "PE13/PE12 W pair"),
    ]:
        require(source, pattern, label, errors)

    expected_dtg = {600: 0x9A, 700: 0xA9, 800: 0xB8}
    for ns, expected in expected_dtg.items():
        actual = dtg_encode(ns, 300_000_000)
        if actual != expected:
            errors.append(
                f"GD32 300 MHz dead-time {ns} ns encodes 0x{actual:02x}, "
                f"expected 0x{expected:02x}"
            )

    root = ET.parse(project).getroot()
    targets = root.findall("./Targets/Target")
    names = [target.findtext("TargetName", default="") for target in targets]
    if set(names) != set(PROFILES):
        errors.append(f"GD32 Keil target set mismatch: {names}")

    for target in targets:
        name = target.findtext("TargetName", default="")
        if name not in PROFILES:
            continue
        duty, dead, profile_id = PROFILES[name]
        device = target.findtext("./TargetOption/TargetCommonOption/Device", default="")
        pack = target.findtext("./TargetOption/TargetCommonOption/PackID", default="")
        ac6 = target.findtext("uAC6", default="")
        clang_as = target.findtext(
            "./TargetOption/TargetArmAds/Aads/ClangAsOpt", default=""
        )
        output = target.findtext(
            "./TargetOption/TargetCommonOption/OutputDirectory", default=""
        )
        hex_enable = target.findtext(
            "./TargetOption/TargetCommonOption/CreateHexFile", default=""
        )
        raw_defs = target.findtext(
            "./TargetOption/TargetArmAds/Cads/VariousControls/Define", default=""
        )
        defs = parse_defines(raw_defs)

        if device != "GD32H75EYMJ6":
            errors.append(f"{name}: wrong GD32 device {device}")
        if pack != "GigaDevice.GD32H75E_DFP.1.4.0":
            errors.append(f"{name}: wrong GD32 DFP {pack}")
        if ac6 != "1" or clang_as != "4":
            errors.append(f"{name}: AC6/startup assembler mode mismatch")
        if name not in output:
            errors.append(f"{name}: GD32 output directory is not target-specific")
        if hex_enable != "1":
            errors.append(f"{name}: GD32 HEX output disabled")
        if "USE_STDPERIPH_DRIVER" not in defs or "GD32H75E" not in defs:
            errors.append(f"{name}: missing GD32 SPL defines")

        expected = {
            "PWM_FREQUENCY_HZ": "20000UL",
            "PWM_DUTY_PERMILLE": f"{duty}UL",
            "PWM_DEADTIME_NS": f"{dead}UL",
            "PWM_PROFILE_ID": f"{profile_id}UL",
        }
        for key, value in expected.items():
            if defs.get(key) != value:
                errors.append(f"{name}: {key}={defs.get(key)!r}, expected {value!r}")

    for name in PROFILES:
        require(build, re.escape(name), f"GD32 batch target {name}", errors)

    for filename in (
        "gd32h75e.h",
        "system_gd32h75e.h",
        "system_gd32h75e.c",
        "startup_gd32h75e.s",
        "gd32h75e_gpio.h",
        "gd32h75e_rcu.h",
        "gd32h75e_timer.h",
        "gd32h75e_gpio.c",
        "gd32h75e_rcu.c",
        "gd32h75e_timer.c",
    ):
        require(prep, re.escape(filename), f"GD32 vendor file {filename}", errors)

    for pin in ("PA8", "PA7", "PE11", "PB0", "PE13", "PE12"):
        require(readme, pin, f"GD32 pin {pin}", errors)
    for bbb in ("P9_29", "P9_30", "P9_28", "P9_27", "P8_16", "P8_15"):
        require(readme, bbb, f"GD32 BBB destination {bbb}", errors)


def main() -> int:
    errors: list[str] = []
    try:
        check_common_profiles(errors)
        check_hpm(errors)
        check_gd32(errors)
    except (ET.ParseError, OSError, ValueError) as exc:
        errors.append(str(exc))

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("HPM6E/GD32H75E PWM stimulus checks: PASS")
    print("  common profiles:", ", ".join(PROFILES))
    print("  HPM6E00EVK: HPM_PWM1 PWMV2, PE08..PE13")
    print("  GD32H75EY-EVAL: TIMER0, PA8/PA7 PE11/PB0 PE13/PE12")
    print("  GD32 dead-time @ 300 MHz: 600ns=0x9a 700ns=0xa9 800ns=0xb8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
