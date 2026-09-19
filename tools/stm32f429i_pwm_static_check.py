#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "boards/stm32f429i_disc1"
PROFILE = BASE / "Inc/pwm_profile.h"
REGS = BASE / "Inc/stm32f429_regs.h"
MAIN = BASE / "Src/main.c"
SYSTEM = BASE / "Src/system_stm32f4xx.c"
STARTUP = BASE / "Startup/startup_stm32f429xx.s"
PROJECT = BASE / "MDK-ARM/hil_pwm_stimulus.uvprojx"
README = BASE / "README.md"
BUILD_ALL = BASE / "MDK-ARM/build_all.bat"
FLASH_BAT = BASE / "MDK-ARM/flash.bat"
SCATTER = BASE / "MDK-ARM/stm32f429_flash.sct"

EXPECTED_TARGETS = {
    "20k_50_600ns": (500, 600, 1),
    "20k_50_700ns": (500, 700, 2),
    "20k_50_800ns": (500, 800, 3),
    "20k_5_700ns": (50, 700, 4),
    "20k_25_700ns": (250, 700, 5),
    "20k_75_700ns": (750, 700, 6),
    "20k_95_700ns": (950, 700, 7),
}


def require(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is None:
        errors.append(f"missing {label}: /{pattern}/")


def forbid(text: str, pattern: str, label: str, errors: list[str]) -> None:
    if re.search(pattern, text, re.MULTILINE) is not None:
        errors.append(f"forbidden {label}: /{pattern}/")


def deadtime_ns_to_dtg(deadtime_ns: int, timer_hz: int = 180_000_000) -> int:
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


def dtg_to_ticks(dtg: int) -> int:
    if (dtg & 0x80) == 0:
        return dtg
    if (dtg & 0xC0) == 0x80:
        return (64 + (dtg & 0x3F)) * 2
    if (dtg & 0xE0) == 0xC0:
        return (32 + (dtg & 0x1F)) * 8
    return (32 + (dtg & 0x1F)) * 16


def parse_defines(raw: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in raw.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def main() -> int:
    errors: list[str] = []

    for path in (PROFILE, REGS, MAIN, SYSTEM, STARTUP, PROJECT, README, BUILD_ALL, FLASH_BAT, SCATTER):
        if not path.is_file():
            errors.append(f"missing required Keil project file: {path.relative_to(ROOT)}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    profile = PROFILE.read_text(encoding="utf-8")
    regs = REGS.read_text(encoding="utf-8")
    source = MAIN.read_text(encoding="utf-8")
    system = SYSTEM.read_text(encoding="utf-8")
    startup = STARTUP.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")
    build_all = BUILD_ALL.read_text(encoding="utf-8")
    flash_bat = FLASH_BAT.read_text(encoding="utf-8")
    scatter = SCATTER.read_text(encoding="utf-8")

    if (BASE / "platformio.ini").exists():
        errors.append("PlatformIO project must not exist; Keil MDK is authoritative")

    for legacy in (BASE / "include", BASE / "src"):
        if legacy.exists():
            errors.append(f"legacy PlatformIO-style directory remains: {legacy.relative_to(ROOT)}")

    for pattern, label in [
        (r"HIL_PLL_SYSCLK_HZ\s+\(180000000UL\)", "180 MHz PLL SYSCLK"),
        (r"HIL_HSI_HZ\s+\(16000000UL\)", "16 MHz reset HSI"),
        (r"HIL_HSE_XTAL_HZ\s+\(8000000UL\)", "8 MHz E01 X3 crystal reference"),
        (r"PWM_FREQUENCY_HZ\s+\(20000UL\)", "20 kHz default PWM"),
        (r"PWM_DUTY_PERMILLE\s+\(500UL\)", "50% default duty"),
        (r"PWM_DEADTIME_NS\s+\(700UL\)", "700 ns default dead-time"),
    ]:
        require(profile, pattern, label, errors)

    period_ticks = 180_000_000 // 20_000
    if period_ticks != 9000 or period_ticks - 1 != 8999:
        errors.append("20 kHz timer period is not ARR=8999")
    if (period_ticks * 500) // 1000 != 4500:
        errors.append("50% reference duty is not CCR1=4500")

    expected_dtg = {600: 0x6C, 700: 0x7E, 800: 0x88}
    for ns, expected in expected_dtg.items():
        dtg = deadtime_ns_to_dtg(ns)
        actual_ns = dtg_to_ticks(dtg) * 1_000_000_000 / 180_000_000
        if dtg != expected:
            errors.append(f"{ns} ns encodes as 0x{dtg:02x}, expected 0x{expected:02x}")
        if abs(actual_ns - ns) > 0.01:
            errors.append(f"{ns} ns decodes to {actual_ns} ns")

    for pattern, label in [
        (r"TIM8_ARR\s*=\s*period_ticks - 1UL", "runtime TIM8 ARR programming"),
        (r"TIM8_CCR1\s*=\s*duty_ticks", "runtime TIM8 CCR1 programming"),
        (r"TIM8_CCER\s*=\s*TIM_CCER_CC1E \| TIM_CCER_CC1NE", "CH1/CH1N enable"),
        (r"TIM8_BDTR\s*=\s*\(dtg & 0xFFUL\) \| TIM_BDTR_MOE", "DTG/MOE programming"),
        (r"RCC_PLLCFGR\s*=", "PLL configuration"),
        (r"360UL << 6", "PLLN 360"),
        (r"\(8UL << 0\)", "HSE crystal PLLM=8"),
        (r"RCC_CFGR_PPRE2_DIV2", "APB2 divider 2"),
        (r"RCC_CR &= ~RCC_CR_HSEBYP", "HSE crystal non-bypass mode"),
        (r"wait_rcc_cr_clear\(RCC_CR_HSERDY\)", "HSE disabled before bypass change"),
        (r"RCC_PLLCFGR_PLLSRC_HSE", "PLL source HSE"),
        (r"CLOCK_SOURCE_HSE_XTAL_PLL", "HSE crystal clock source state"),
        (r"wait_rcc_cr_set\(RCC_CR_HSERDY\)", "required HSE readiness test"),
        (r"g_clock_fault_flags \|= CLOCK_FAULT_HSE_TIMEOUT", "HSE timeout fault latch"),
        (r"deadtime_ns_to_dtg\(PWM_DEADTIME_NS, timer_clock_hz\)", "runtime dead-time clock"),
        (r"g_pwm_deadtime_actual_ns", "quantized dead-time diagnostic"),
        (r"g_boot_stage", "boot-stage diagnostic"),
        (r"GPIOC_BASE", "PC6 main output"),
        (r"GPIOA_BASE", "PA5 complementary output"),
    ]:
        require(source, pattern, label, errors)

    forbid(source, r"stm32f4xx_hal|HAL_", "STM32Cube HAL dependency", errors)
    forbid(source, r"RCC_CR\s*\|=\s*RCC_CR_HSEBYP", "HSE bypass mode on E01 crystal reference", errors)
    forbid(source, r"CLOCK_SOURCE_HSI_PLL|use_direct_hsi:", "HSI timing fallback", errors)
    require(regs, r"TIM8_BASE\s+0x40010400UL", "TIM8 register base", errors)
    require(regs, r"RCC_CR_HSION\s+\(1UL << 0\)", "HSI enable bit", errors)
    require(regs, r"RCC_CR_HSIRDY\s+\(1UL << 1\)", "HSI ready bit", errors)
    require(system, r"SystemCoreClock\s*=\s*180000000UL", "180 MHz PLL system core update", errors)
    require(system, r"SystemCoreClock\s*=\s*16000000UL", "16 MHz reset SystemCoreClock", errors)
    require(startup, r"Reset_Handler", "MDK reset handler", errors)
    require(startup, r"IMPORT\s+SystemInit", "startup SystemInit import", errors)

    try:
        root = ET.parse(PROJECT).getroot()
    except ET.ParseError as exc:
        errors.append(f"invalid Keil uvprojx XML: {exc}")
        root = None

    if root is not None:
        targets = root.findall("./Targets/Target")
        names = [target.findtext("TargetName", default="") for target in targets]
        if set(names) != set(EXPECTED_TARGETS):
            errors.append(f"Keil target set mismatch: {names}")

        for target in targets:
            name = target.findtext("TargetName", default="")
            if name not in EXPECTED_TARGETS:
                continue

            duty, dead, profile_id = EXPECTED_TARGETS[name]
            device = target.findtext("./TargetOption/TargetCommonOption/Device", default="")
            pack = target.findtext("./TargetOption/TargetCommonOption/PackID", default="")
            ac6 = target.findtext("uAC6", default="")
            target_dll = target.findtext("./TargetOption/DllOption/TargetDllName", default="")
            use_target_dll = target.findtext("./TargetOption/Utilities/Flash1/UseTargetDll", default="")
            update_flash_before_debug = target.findtext("./TargetOption/Utilities/Flash1/UpdateFlashBeforeDebugging", default="")
            flash2 = target.findtext("./TargetOption/Utilities/Flash2", default="")
            clang_as = target.findtext("./TargetOption/TargetArmAds/Aads/ClangAsOpt", default="")
            output = target.findtext("./TargetOption/TargetCommonOption/OutputDirectory", default="")
            hex_enable = target.findtext("./TargetOption/TargetCommonOption/CreateHexFile", default="")
            use_target_memory = target.findtext("./TargetOption/TargetArmAds/LDads/umfTarg", default="")
            use_scatter = target.findtext("./TargetOption/TargetArmAds/LDads/useFile", default="")
            scatter_file = target.findtext("./TargetOption/TargetArmAds/LDads/ScatterFile", default="")
            defines_raw = target.findtext(
                "./TargetOption/TargetArmAds/Cads/VariousControls/Define",
                default="",
            )
            defines = parse_defines(defines_raw)

            if device != "STM32F429ZITx":
                errors.append(f"{name}: wrong device {device}")
            if pack != "Keil.STM32F4xx_DFP.3.1.1":
                errors.append(f"{name}: wrong DFP {pack}")
            if ac6 != "1":
                errors.append(f"{name}: Arm Compiler 6 is not enabled")
            if target_dll != "SARMCM3.DLL":
                errors.append(f"{name}: non-portable target DLL {target_dll!r}")
            if use_target_dll != "0":
                errors.append(f"{name}: repository project must not require a hardware debugger DLL")
            if update_flash_before_debug != "0":
                errors.append(f"{name}: repository project must not auto-flash before debug")
            if flash2 != r"BIN\UL2CM3.DLL":
                errors.append(f"{name}: unexpected portable flash DLL {flash2!r}")
            if clang_as != "4":
                errors.append(f"{name}: startup assembler is not in AC6 legacy Arm-syntax mode")
            if name not in output:
                errors.append(f"{name}: output directory is not target-specific")
            if hex_enable != "1":
                errors.append(f"{name}: HEX output is disabled")
            if use_target_memory != "0":
                errors.append(f"{name}: Use Memory Layout from Target Dialog must be disabled")
            if use_scatter != "1":
                errors.append(f"{name}: explicit scatter file is not enabled")
            if scatter_file != r".\stm32f429_flash.sct":
                errors.append(f"{name}: wrong scatter file {scatter_file!r}")

            expected_defs = {
                "PWM_FREQUENCY_HZ": "20000UL",
                "PWM_DUTY_PERMILLE": f"{duty}UL",
                "PWM_DEADTIME_NS": f"{dead}UL",
                "PWM_PROFILE_ID": f"{profile_id}UL",
            }
            for key, expected in expected_defs.items():
                if defines.get(key) != expected:
                    errors.append(
                        f"{name}: {key}={defines.get(key)!r}, expected {expected!r}"
                    )

            file_paths = {
                node.text or ""
                for node in target.findall("./Groups/Group/Files/File/FilePath")
            }
            for expected_path in (
                r"..\Src\main.c",
                r"..\Src\system_stm32f4xx.c",
                r"..\Startup\startup_stm32f429xx.s",
                r"..\Inc\pwm_profile.h",
                r"..\Inc\stm32f429_regs.h",
            ):
                if expected_path not in file_paths:
                    errors.append(f"{name}: missing project file {expected_path}")

    require(readme, r"hil_pwm_stimulus\.uvprojx", "Keil project open instructions", errors)
    require(readme, r"20k_50_700ns", "default Keil Target documentation", errors)
    require(readme, r"P9_29", "BBB UH destination", errors)
    require(readme, r"P9_30", "BBB UL destination", errors)
    require(readme, r"build_all\.bat", "Keil batch-build documentation", errors)
    require(readme, r"MB1075-F429I-E01", "qualified PCB revision", errors)
    require(readme, r"X3 8 MHz", "E01 crystal reference", errors)
    require(readme, r"HSEBYP\s*=\s*0", "crystal-mode HSE documentation", errors)
    require(readme, r"HSI fallback is not accepted", "fail-closed timing qualification policy", errors)
    forbid(PROJECT.read_text(encoding="utf-8"), r"ST-LINKIII-KEIL_SWO\.dll", "hard-coded ST-Link debugger DLL", errors)
    require(flash_bat, r"STM32_Programmer_CLI\.exe", "STM32CubeProgrammer flash helper", errors)
    require(flash_bat, r"-c port=SWD -w", "SWD flash command", errors)
    for target_name in EXPECTED_TARGETS:
        require(
            build_all,
            re.escape(target_name),
            f"build_all target {target_name}",
            errors,
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("STM32F429I-DISC1 Keil PWM stimulus checks: PASS")
    print("  project: MDK-ARM/hil_pwm_stimulus.uvprojx")
    print("  linker: explicit stm32f429_flash.sct (Flash RO + SRAM RW/ZI)")
    print("  targets:", ", ".join(EXPECTED_TARGETS))
    print("  nominal PLL mode: 20 kHz -> ARR=8999, CCR1=4500")
    print("  clock reference: MB1075-F429I-E01 X3 8 MHz -> HSE PLL -> TIM8 180 MHz")
    print("  dead-time: 600ns=0x6c, 700ns=0x7e, 800ns=0x88")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
