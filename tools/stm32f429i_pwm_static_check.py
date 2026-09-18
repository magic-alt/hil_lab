#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "boards/stm32f429i_disc1"
PROFILE = BASE / "include/pwm_profile.h"
MAIN = BASE / "src/main.c"
PIO = BASE / "platformio.ini"
README = BASE / "README.md"


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
        scaled = (ticks + 1) // 2
        scaled = max(64, min(127, scaled))
        return 0x80 | (scaled - 64)
    if ticks <= 504:
        scaled = (ticks + 4) // 8
        scaled = max(32, min(63, scaled))
        return 0xC0 | (scaled - 32)

    scaled = (ticks + 8) // 16
    scaled = max(32, min(63, scaled))
    return 0xE0 | (scaled - 32)


def dtg_to_ticks(dtg: int) -> int:
    if (dtg & 0x80) == 0:
        return dtg
    if (dtg & 0xC0) == 0x80:
        return (64 + (dtg & 0x3F)) * 2
    if (dtg & 0xE0) == 0xC0:
        return (32 + (dtg & 0x1F)) * 8
    return (32 + (dtg & 0x1F)) * 16


def main() -> int:
    errors: list[str] = []
    profile = PROFILE.read_text(encoding="utf-8")
    source = MAIN.read_text(encoding="utf-8")
    pio = PIO.read_text(encoding="utf-8")
    readme = README.read_text(encoding="utf-8")

    for pattern, label in [
        (r"HIL_SYSCLK_HZ\s+\(180000000UL\)", "180 MHz SYSCLK"),
        (r"HIL_APB2_TIMER_HZ\s+\(180000000UL\)", "180 MHz TIM8 clock"),
        (r"PWM_FREQUENCY_HZ\s+\(20000UL\)", "20 kHz default PWM"),
        (r"PWM_DUTY_PERMILLE\s+\(500UL\)", "50% default duty"),
        (r"PWM_DEADTIME_NS\s+\(700UL\)", "700 ns default dead-time"),
    ]:
        require(profile, pattern, label, errors)

    period_ticks = 180_000_000 // 20_000
    if period_ticks != 9000:
        errors.append(f"unexpected 20 kHz period ticks: {period_ticks}")
    if period_ticks - 1 != 8999:
        errors.append("unexpected ARR")
    if (period_ticks * 500) // 1000 != 4500:
        errors.append("unexpected CCR1")

    expected = {
        600: (0x6C, 600.0),
        700: (0x7E, 700.0),
        800: (0x88, 800.0),
    }
    for ns, (expected_dtg, expected_actual_ns) in expected.items():
        dtg = deadtime_ns_to_dtg(ns)
        actual_ns = dtg_to_ticks(dtg) * 1_000_000_000 / 180_000_000
        if dtg != expected_dtg:
            errors.append(f"{ns} ns encodes as 0x{dtg:02x}, expected 0x{expected_dtg:02x}")
        if abs(actual_ns - expected_actual_ns) > 0.01:
            errors.append(f"{ns} ns decodes to {actual_ns} ns")

    for pattern, label in [
        (r"htim8\.Instance\s*=\s*TIM8", "TIM8 instance"),
        (r"GPIO_AF3_TIM8", "TIM8 AF3 GPIO"),
        (r"GPIO_PIN_6", "PC6 main output"),
        (r"GPIO_PIN_5", "PA5 complementary output"),
        (r"HAL_TIM_PWM_Start\(&htim8,\s*TIM_CHANNEL_1\)", "TIM8 CH1 start"),
        (r"HAL_TIMEx_PWMN_Start\(&htim8,\s*TIM_CHANNEL_1\)", "TIM8 CH1N start"),
        (r"RCC_HSE_BYPASS", "DISC1 ST-LINK MCO clock mode"),
        (r"osc\.PLL\.PLLM\s*=\s*8U", "PLLM=8"),
        (r"osc\.PLL\.PLLN\s*=\s*360U", "PLLN=360"),
        (r"RCC_PLLP_DIV2", "PLLP=2"),
        (r"RCC_HCLK_DIV2", "APB2 divider=2"),
    ]:
        require(source, pattern, label, errors)

    forbid(source, r"GPIO_PIN_8|GPIO_PIN_9", "PE8/PE9 TIM1 stimulus pins", errors)

    require(pio, r"board\s*=\s*disco_f429zi", "PlatformIO disco_f429zi board", errors)
    for env in (
        "disco_f429zi_20k_50_600ns",
        "disco_f429zi_20k_50_700ns",
        "disco_f429zi_20k_50_800ns",
        "disco_f429zi_20k_5_700ns",
        "disco_f429zi_20k_25_700ns",
        "disco_f429zi_20k_75_700ns",
        "disco_f429zi_20k_95_700ns",
    ):
        require(pio, rf"\[env:{re.escape(env)}\]", f"PlatformIO profile {env}", errors)

    require(readme, r"PC6.*TIM8_CH1.*P1 pin 57", "UH wiring documentation", errors)
    require(readme, r"PA5.*TIM8_CH1N.*P2 pin 21", "UL wiring documentation", errors)
    require(readme, r"P9_29", "BBB UH destination", errors)
    require(readme, r"P9_30", "BBB UL destination", errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("STM32F429I-DISC1 PWM stimulus checks: PASS")
    print("  20 kHz: ARR=8999, CCR1=4500")
    print("  dead-time: 600ns=0x6c, 700ns=0x7e, 800ns=0x88")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
