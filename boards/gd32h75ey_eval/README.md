# GD32H75EY-EVAL six-PWM stimulus for BBB B1

Native Keil MDK-ARM no-motor six-PWM source for BBB B1.

## Target

- Board: GD32H75EY-EVAL
- MCU: GD32H75EYMJ6
- Advanced timer: TIMER0
- Build: Keil MDK / Arm Compiler 6
- DFP baseline: GigaDevice.GD32H75E_DFP.1.4.0
- Firmware library baseline: GD32H75E Firmware Library 1.3.0

The project keeps the application and Keil project in git, while the official
firmware library is prepared locally as a vendor dependency.

## Six-channel map

| Signal | GD32H75EY-EVAL MCU pin | Function | BBB |
| --- | --- | --- | --- |
| UH | PA8 | TIMER0_CH0 AF1 | P9_29 |
| UL | PA7 | TIMER0_MCH0 AF1 | P9_30 |
| VH | PE11 | TIMER0_CH1 AF1 | P9_28 |
| VL | PB0 | TIMER0_MCH1 AF1 | P9_27 |
| WH | PE13 | TIMER0_CH2 AF1 | P8_16 |
| WL | PE12 | TIMER0_MCH2 AF1 | P8_15 |
| GND | GND | - | GND |

These are the PWM0 pins used by the current GD32H75EY-EVAL board definition.
Confirm physical header/test-point locations against your EVAL board schematic.

## Profiles

The Keil project contains:

    20k_50_600ns
    20k_50_700ns
    20k_50_800ns
    20k_5_700ns
    20k_25_700ns
    20k_75_700ns
    20k_95_700ns

All U/V/W phases intentionally use the same duty and phase.

## Prepare the official library

Download/extract the official GD32H75E Firmware Library, then:

    powershell -ExecutionPolicy Bypass -File prepare_vendor.ps1 -SourceRoot D:\SDK\GD32H75E_Firmware_Library

The script copies only the required CMSIS/device/GPIO/RCU/TIMER files into the
ignored Vendor directory.

## Keil

Open:

    MDK-ARM\hil_pwm_stimulus.uvprojx

Select 20k_50_700ns first, Build, and Download with your normal GD-Link/ST-Link
setup.

All targets generate independent Objects/<target> and HEX outputs.

Batch build:

    MDK-ARM\build_all.bat

## Clock and timer

The official GD32H75E system file selects a 600 MHz core reference
configuration. In that configuration AHB/APB2 are 300 MHz. This application
also queries CK_AHB and CK_APB2 at runtime and configures
RCU_TIMER_PSC_MUL4, so TIMER0 clock is derived rather than blindly hard-coded.

Reference 300 MHz values:

    20 kHz period = 15000 ticks
    ARR = 14999
    50% pulse = 7500 ticks
    600 ns = DTG 0x9a
    700 ns = DTG 0xa9
    800 ns = DTG 0xb8

Debug globals expose the actual timer clock, period, pulse, DTG and quantized
dead-time.

## BBB

Wire all six signals plus common GND, deploy BBB B1, then run the usual
hil_pwm_cli.py config/start/snapshot flow.

## Safety

Logic stimulus only. Do not connect directly to MOSFET gates, motor phases,
brake power or the DC bus.
