# STM32F429I-DISC1 complementary PWM stimulus

This board project generates the first physical stimulus for BBB B1 (#12):
one 20 kHz complementary PWM pair with programmable duty and dead-time.

## Default waveform

```text
PWM frequency : 20 kHz
period        : 50 us
reference duty: 50%
dead-time     : 700 ns
logic level   : 3.3 V
timer         : TIM8 CH1 / CH1N
timer clock   : 180 MHz
```

The timer runs edge-aligned with:

```text
PSC  = 0
ARR  = 8999
CCR1 = 4500
```

At 180 MHz, `tDTS = 5.555... ns`. The default 700 ns request encodes as
`DTG=126`, therefore:

```text
126 * 5.555... ns = 700 ns
```

For 800 ns, the encoder automatically moves into the STM32F4 DTG `10x`
range rather than truncating at 127 ticks.

## Why TIM8 / PC6 + PA5

Do **not** use TIM1 PE8/PE9 on STM32F429I-DISC1 for this test. Those pins are
wired to the onboard SDRAM data bus.

The selected pins are:

| Signal | STM32 pin | Timer function | DISC1 header | Connect to BBB |
| --- | --- | --- | --- | --- |
| UH | PC6 | TIM8_CH1 | P1 pin 57 | P9_29 / PRU0 R31[1] |
| UL | PA5 | TIM8_CH1N | P2 pin 21 | P9_30 / PRU0 R31[2] |
| GND | any board GND | - | any GND | any BBB GND |

PC6 is also connected to the onboard LCD HSYNC input. This firmware does not
initialize LTDC, so there is no MCU-side output contention; the LCD may flicker
or show invalid content while PC6 is used as PWM.

PA5 is otherwise unused by the onboard application hardware.

## Clock assumption

The factory STM32F429I-DISC1 clock configuration routes the ST-LINK MCO to
PH0/OSC_IN at a fixed 8 MHz. This firmware therefore uses:

```text
HSE bypass = 8 MHz ST-LINK MCO
PLL        = 8 / 8 * 360 / 2 = 180 MHz SYSCLK
APB2       = 90 MHz
TIM8 clock = 180 MHz
```

Keep the ST-LINK USB connected while using the default factory clock routing.
If the board solder bridges were modified for an X3 crystal or external PH0
clock, adapt `SystemClock_Config()` accordingly.

## Build and flash

This stimulus is packaged as a PlatformIO project because PlatformIO already
supports STM32F429I-DISC1 under board ID `disco_f429zi` and can use the
on-board ST-LINK.

Install PlatformIO Core, then:

```bash
cd boards/stm32f429i_disc1

pio run
pio run -t upload
```

The default environment is:

```text
disco_f429zi_20k_50_700ns
```

LD3 (green, PG13) turns on after TIM8 CH1/CH1N have both started.

## Sweep profiles

Predefined environments:

```text
disco_f429zi_20k_50_600ns
disco_f429zi_20k_50_700ns
disco_f429zi_20k_50_800ns

disco_f429zi_20k_5_700ns
disco_f429zi_20k_25_700ns
disco_f429zi_20k_50_700ns
disco_f429zi_20k_75_700ns
disco_f429zi_20k_95_700ns
```

Example:

```bash
pio run -e disco_f429zi_20k_50_800ns -t upload
```

You can also override the compile-time values in another PlatformIO
environment:

```ini
build_flags =
  -D PWM_FREQUENCY_HZ=20000UL
  -D PWM_DUTY_PERMILLE=500UL
  -D PWM_DEADTIME_NS=700UL
```

## BBB connection

Power the two boards independently through their normal USB supplies, then
connect the grounds.

```text
STM32F429I-DISC1                  BeagleBone Black

P1-57 / PC6 / TIM8_CH1   UH  --> P9_29 / PRU0 R31[1]
P2-21 / PA5 / TIM8_CH1N  UL  --> P9_30 / PRU0 R31[2]
GND                          --> GND
```

Do not connect 5 V or any gate-driver/power-stage node to the BBB inputs.

Configure BBB:

```bash
cd ~/hil_lab/boards/beaglebone_black
sudo python3 scripts/pru0_ctl.py stop
sudo sh ./pinmux/setup_b1_pwm_inputs.sh
sudo python3 scripts/pru0_ctl.py \
  deploy firmware/pru0_b1/gen/hil_b1_pru0.out
```

Then:

```bash
cd host

python3 hil_pwm_cli.py config --min-deadtime-ns 700
python3 hil_pwm_cli.py clear
python3 hil_pwm_cli.py start
sleep 1
sudo -E python3 hil_pwm_cli.py snapshot --ring-limit 16
python3 hil_pwm_cli.py stop
```

## Expected B1 measurements

At 20 kHz:

```text
period_ticks ~= 10000
period_us    ~= 50.000
```

For the default 700 ns dead-time:

```text
deadtime_ticks ~= 140
deadtime_ns    ~= 700
overlap_count  = 0
violation_count should be 0 when the B1 threshold is <= the measured dead-time
```

Because the advanced timer dead-time generator delays turn-on edges, the
individual UH/UL high pulse width is expected to be approximately the reference
25 us minus one dead-time interval, rather than exactly 25 us. Use the
oscilloscope value as the physical reference.

## Independent measurement

Probe the DISC1 pins or BBB input pins with an oscilloscope / logic analyzer:

```text
CH1 -> UH / PC6 / P1-57
CH2 -> UL / PA5 / P2-21
GND -> common GND
```

Verify:

- 20 kHz / ~50 us period;
- no UH/UL overlap;
- H->L dead-time near the selected value;
- L->H dead-time near the selected value;
- compare both dead-times with the BBB shared-RAM snapshot.

## Safety

This project is a 3.3 V digital stimulus only. It is not a gate-driver or
power-stage generator. Do not wire these outputs directly into MOSFET gates,
24/48 V domains, motor phases, brake wiring or the DC bus.
