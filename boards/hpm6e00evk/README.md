# HPM6E00EVK six-PWM stimulus for BBB B1

HPM SDK-native no-motor PWM source for BBB B1.

## Hardware
- HPM6E00EVK
- HPM_PWM1 / PWMV2 pair mode
- PE08..PE13 = PWM1_P0..P5

## Wiring
| Signal | HPM6E00EVK | BBB |
| --- | --- | --- |
| UH | PE08 / PWM1_P0 | P9_29 |
| UL | PE09 / PWM1_P1 | P9_30 |
| VH | PE10 / PWM1_P2 | P9_28 |
| VL | PE11 / PWM1_P3 | P9_27 |
| WH | PE12 / PWM1_P4 | P8_16 |
| WL | PE13 / PWM1_P5 | P8_15 |
| GND | GND | GND |

Confirm physical connector numbering against the EVK revision schematic.

## Profiles
20k_50_600ns, 20k_50_700ns, 20k_50_800ns,
20k_5_700ns, 20k_25_700ns, 20k_75_700ns, 20k_95_700ns.

All U/V/W pairs intentionally use the same duty and phase for capture
characterization.

## Build
Set HPM_SDK_BASE and the HPM RISC-V toolchain environment.

One profile:

    cmake -S . -B build/20k_50_700ns -G Ninja -DBOARD=hpm6e00evk -DHIL_PWM_PROFILE=20k_50_700ns -DCMAKE_BUILD_TYPE=release
    cmake --build build/20k_50_700ns

All profiles on Windows:

    .\build_all.ps1

The firmware derives reload and dead-zone ticks from the actual clock_pwm1
frequency at runtime.

## BBB capture
Use the existing B1 firmware and hil_pwm_cli.py. Start with
20k_50_700ns, then sweep dead-time and duty.

## Safety
3.3 V logic stimulus only. No motor, gate-driver, brake, phase or DC-bus
connection.
