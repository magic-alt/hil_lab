# STM32F429I-DISC1 Keil PWM stimulus

This is a native **Keil MDK-ARM / uVision** project used as the physical PWM
stimulus source for BeagleBone Black B1 (#12).

PlatformIO is intentionally not used.

## Project

Open:

```text
boards/stm32f429i_disc1/MDK-ARM/hil_pwm_stimulus.uvprojx
```

The project contains seven Keil Targets. Select the desired waveform directly
from the uVision target drop-down:

```text
20k_50_600ns
20k_50_700ns   <- recommended first B1 test
20k_50_800ns

20k_5_700ns
20k_25_700ns
20k_75_700ns
20k_95_700ns
```

All Targets compile the same source files. Only target-level preprocessor
definitions change:

```text
PWM_FREQUENCY_HZ
PWM_DUTY_PERMILLE
PWM_DEADTIME_NS
PWM_PROFILE_ID
```

That keeps waveform configuration out of source-code forks.

## Keil requirements

- Keil MDK-ARM / uVision with Arm Compiler 6. The project file was created with AC6.18 metadata, but the source does not depend on 6.18 specifically; if uVision reports that compiler version is unavailable, select any installed Arm Compiler 6 under **Options for Target -> Target -> ARM Compiler**.
- Device: `STM32F429ZITx`.
- CMSIS Device Family Pack: `Keil::STM32F4xx_DFP@3.1.1`.

Pack 3.1.1 is the current repository baseline. Install it with Keil Pack
Installer or CMSIS Toolbox:

```text
cpackget add Keil::STM32F4xx_DFP@3.1.1
```

The application does **not** depend on STM32Cube HAL. RCC, GPIO and TIM8 are
configured directly with local register definitions.

The startup file and system initialization file are committed with this
repository, so the project does not depend on the Device:Startup component
removed from newer STM32F4 DFP releases. The startup source is assembled with
uVision's Arm Compiler 6 legacy Arm-syntax assembler compatibility mode.

The project also uses an explicit Arm Compiler 6 scatter file:

```text
MDK-ARM/stm32f429_flash.sct
```

It places read-only code/data in internal Flash at `0x08000000` and the default
RW/ZI region in SRAM at `0x20000000`. This avoids uVision auto-scatter ambiguity
that can otherwise produce `Scatter Error: no default 'Read/Write' range selected`
on some MDK/Compiler 6 installations.

In every Keil Target, **Use Memory Layout from Target Dialog is disabled** (`umfTarg=0`) and the explicit scatter file is enabled (`useFile=1`). If `umfTarg` is left at `1`, uVision ignores the repository scatter file and tries to generate/use an `Objects\\<target>\\*.sct` file instead.

## Directory layout

```text
stm32f429i_disc1/
├── MDK-ARM/
│   └── hil_pwm_stimulus.uvprojx
├── Inc/
│   ├── pwm_profile.h
│   └── stm32f429_regs.h
├── Src/
│   ├── main.c
│   └── system_stm32f4xx.c
├── Startup/
│   └── startup_stm32f429xx.s
└── README.md
```

Generated Keil output is kept below:

```text
MDK-ARM/Objects/<target>/
MDK-ARM/Listings/<target>/
```

Each Target produces an independent AXF and HEX file.

## Default 20 kHz / 50% / 700 ns waveform

For Target `20k_50_700ns`:

```text
TIM8 clock     = 180 MHz
PWM frequency  = 20 kHz
period         = 50 us
PSC            = 0
ARR            = 8999
CCR1           = 4500
requested DT   = 700 ns
DTG            = 0x7e
logic          = 3.3 V
```

The project uses edge-aligned TIM8 PWM1 with complementary CH1/CH1N outputs.

The STM32F4 advanced-timer dead-time encoder is implemented across all DTG
ranges. The repository checker verifies:

```text
600 ns -> DTG 0x6c
700 ns -> DTG 0x7e
800 ns -> DTG 0x88
```

## Pin selection

Do **not** use TIM1 PE8/PE9 on STM32F429I-DISC1 for this test; those pins are
connected to the onboard SDRAM data bus.

The Keil stimulus uses TIM8:

| Signal | STM32 pin | Timer | DISC1 header | BBB |
| --- | --- | --- | --- | --- |
| UH | PC6 | TIM8_CH1 | P1 pin 57 | P9_29 / PRU0 R31[1] |
| UL | PA5 | TIM8_CH1N | P2 pin 21 | P9_30 / PRU0 R31[2] |
| GND | board GND | - | any GND | BBB GND |

PC6 is also connected to the onboard LCD HSYNC input. This project does not
initialize LTDC, so there is no MCU output conflict; the onboard display may
show invalid content while PC6 is used as PWM.

## Clock tree

STM32F429I-DISC1 factory routing provides an 8 MHz ST-LINK MCO clock on
PH0/OSC_IN.

The firmware configures:

```text
HSE bypass      = 8 MHz
PLLM            = 8
PLLN            = 360
PLLP            = 2
SYSCLK          = 180 MHz
AHB             = 180 MHz
APB1            = 45 MHz
APB2            = 90 MHz
TIM8            = 180 MHz
```

Keep the ST-LINK USB connected when using the factory MCO clock path.

## Build and download in Keil

1. Open `MDK-ARM/hil_pwm_stimulus.uvprojx`.
2. Select Target `20k_50_700ns`.
3. Use **Project -> Build Target** (F7).
4. Connect the onboard ST-LINK USB.
5. Use **Flash -> Download**.
6. Reset/run the board.
7. LD3 green on PG13 turns on after TIM8 is started.

The project creates a HEX file for each configuration, for example:

```text
MDK-ARM/Objects/20k_50_700ns/hil_pwm_20k_50_700ns.hex
```

To build all seven Targets from a Windows command prompt:

```bat
cd boards\stm32f429i_disc1\MDK-ARM
build_all.bat
```

The script uses `C:\Keil_v5\UV4\UV4.exe` by default. If Keil is installed
elsewhere, set:

```bat
set KEIL_UVISION=D:\Keil_v5\UV4\UV4.exe
build_all.bat
```

Per-target logs are written to `MDK-ARM\Logs\`.

## Connect to BBB B1

Power both boards normally over USB and connect a common ground:

```text
STM32F429I-DISC1                  BeagleBone Black

P1-57 / PC6 / TIM8_CH1   UH  --> P9_29 / PRU0 R31[1]
P2-21 / PA5 / TIM8_CH1N  UL  --> P9_30 / PRU0 R31[2]
GND                          --> GND
```

Do not connect 5 V or any gate-driver/power-stage signal directly to the BBB.

BBB setup:

```bash
cd ~/hil_lab/boards/beaglebone_black

sudo python3 scripts/pru0_ctl.py stop
sudo sh ./pinmux/setup_b1_pwm_inputs.sh
sudo python3 scripts/pru0_ctl.py \
  deploy firmware/pru0_b1/gen/hil_b1_pru0.out
```

Capture:

```bash
cd host

python3 hil_pwm_cli.py config --min-deadtime-ns 700
python3 hil_pwm_cli.py clear
python3 hil_pwm_cli.py start

sleep 1

sudo -E python3 hil_pwm_cli.py snapshot --ring-limit 16

python3 hil_pwm_cli.py stop
```

Expected first-order B1 values:

```text
period_ticks                 ~= 10000
period_us                    ~= 50.000
deadtime_high_to_low_ticks   ~= 140
deadtime_low_to_high_ticks   ~= 140
overlap_count                = 0
```

Compare the BBB result against an oscilloscope or logic analyzer at the actual
BBB input pins.

## Configuration sweep

Use the Keil target selector to run the planned B1 sweep:

| Keil Target | Reference duty | Requested dead-time |
| --- | ---: | ---: |
| 20k_50_600ns | 50% | 600 ns |
| 20k_50_700ns | 50% | 700 ns |
| 20k_50_800ns | 50% | 800 ns |
| 20k_5_700ns | 5% | 700 ns |
| 20k_25_700ns | 25% | 700 ns |
| 20k_75_700ns | 75% | 700 ns |
| 20k_95_700ns | 95% | 700 ns |

The timer dead-time generator delays turn-on edges, so the physical UH/UL pulse
width after dead-time insertion is not necessarily equal to the nominal
reference duty. The scope measurement is the physical reference.

## Debug variables

The following globals are intentionally retained for the Keil Watch window:

```text
g_pwm_profile_id
g_pwm_frequency_hz
g_pwm_duty_permille
g_pwm_deadtime_ns
g_pwm_deadtime_dtg
SystemCoreClock
```

They make it easy to confirm the selected Keil Target before wiring the BBB.

## Safety

This firmware is a **3.3 V digital stimulus only**.

Do not connect its outputs directly to MOSFET gates, 24/48 V domains, motor
phases, brake wiring or the DC bus.
