# MCU PWM stimulus matrix

The no-motor PWM generators under `boards/` are physical sources for BBB B1
PWM/dead-time capture validation. They intentionally share one profile set.

| Board | Native toolchain | PWM peripheral | Channels | Primary purpose |
| --- | --- | --- | ---: | --- |
| STM32F429I-DISC1 | Keil MDK-ARM | TIM8 CH1/CH1N | 2 | first U-pair timing check |
| HPM6E00EVK | HPM SDK / CMake | HPM_PWM1 / PWMV2 | 6 | HPM servo-controller six-PWM regression |
| GD32H75EY-EVAL | Keil MDK-ARM | TIMER0 CH0..2/MCH0..2 | 6 | GD32 servo-controller six-PWM regression |

## Common profiles

```text
20k_50_600ns
20k_50_700ns
20k_50_800ns
20k_5_700ns
20k_25_700ns
20k_75_700ns
20k_95_700ns
```

Start every board with `20k_50_700ns`.

## BBB logical mapping

```text
UH -> P9_29 / R31[1]
UL -> P9_30 / R31[2]
VH -> P9_28 / R31[3]
VL -> P9_27 / R31[5]
WH -> P8_16 / R31[14]
WL -> P8_15 / R31[15]
```

STM32F429I-DISC1 drives only UH/UL. HPM6E00EVK and GD32H75EY-EVAL drive all
six signals.

## Measurement order

1. Verify source waveform on an oscilloscope before connecting the BBB.
2. Connect common ground.
3. Start with the U pair only where practical.
4. Capture 20 kHz period and both dead-time directions.
5. Run 600/700/800 ns dead-time sweep.
6. Run 5/25/50/75/95% duty sweep.
7. Enable all six channels.
8. Compare BBB measurements against the scope/logic-analyzer reference.
9. Run long-duration edge-count and loss testing.

## Safety

These projects are 3.3 V digital stimulus sources. They do not emulate the
power stage and must not be connected directly to gate-driver power outputs,
MOSFET gates, motor phases, brake power or DC-bus nodes.
