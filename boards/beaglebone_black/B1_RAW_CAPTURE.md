# B1 raw-edge precision capture

This is the precision-capture successor to the original semantics-first
`pru0_b1` firmware.

The original firmware is retained as a measured baseline. Real STM32F429I-DISC1
testing showed that it preserved event order/counts but added about 0.8 us of
post-edge software blind time, causing a physical ~700 ns complementary
dead-time to be observed near 1.55 us.

## Architecture

```text
PRU0 precise window
───────────────────────────────────────
R31 sample
  -> mask six PWM input bits
  -> changed?
      no  -> immediately resample
      yes -> read IEP
          -> store {timestamp, raw_inputs}
          -> increment local count
          -> immediately resample
───────────────────────────────────────
                 |
                 v
        frozen raw edge buffer
                 |
                 v
Linux offline decoder
  -> R31-to-logical mapping
  -> period/high/low
  -> complementary dead-time
  -> overlap
  -> min-dead-time policy
  -> statistics / percentiles
```

No channel loop, pair loop, dead-time arithmetic or streaming statistics is
allowed in the PRU precision edge path.

## Why capture is bounded

The precision mode intentionally captures a configured number of events and
auto-stops. Linux/RPMsg traffic is kept outside the precise measurement window.

Shared RAM holds:

```text
64-byte header
1024 x 8-byte edge records
= 8256 bytes total
```

Each record is only:

```text
uint32 timestamp_ticks
uint32 raw_inputs
```

At one 20 kHz complementary pair there are approximately 80k state changes/s,
so 1024 events cover about 12.8 ms. With all three 20 kHz complementary pairs
switching independently, the same buffer covers a shorter but still useful
precision window.

## Build

On the BBB:

```bash
cd ~/hil_lab

unset PSSP_DIR
export PRU_CGT=/usr/share/ti/cgt-pru

make bbb-b1-raw-pru-env
make bbb-b1-raw-pru-build
```

Expected firmware:

```text
boards/beaglebone_black/firmware/pru0_b1_raw/gen/hil_b1_raw_pru0.out
```

## Deploy

The pin map is unchanged from B1:

```text
UH -> P9_29 -> PRU0 R31[1]
UL -> P9_30 -> PRU0 R31[2]
VH -> P9_28 -> PRU0 R31[3]
VL -> P9_27 -> PRU0 R31[5]
WH -> P8_16 -> PRU0 R31[14]
WL -> P8_15 -> PRU0 R31[15]
```

Deploy:

```bash
cd ~/hil_lab/boards/beaglebone_black

sudo python3 scripts/pru0_ctl.py stop
sudo sh pinmux/setup_b1_pwm_inputs.sh

sudo python3 scripts/pru0_ctl.py deploy \
  firmware/pru0_b1_raw/gen/hil_b1_raw_pru0.out
```

HELLO should report firmware version `0x00020100` and
`raw_edge_capture`.

## First STM32F429 test

Use the already validated physical source:

```text
PC6 / TIM8_CH1  -> BBB P9_29 / UH
PA5 / TIM8_CH1N -> BBB P9_30 / UL
GND             -> BBB GND
```

Start with `20k_50_700ns`.

Run one bounded capture:

```bash
cd ~/hil_lab/boards/beaglebone_black/host

python3 hil_raw_cli.py hello

sudo -E python3 hil_raw_cli.py capture \
  --event-limit 1024 \
  --settle-ms 100 \
  --min-deadtime-ns 600
```

The host intentionally sleeps without RPMsg traffic while PRU0 fills the raw
buffer. Only after the expected capture window has elapsed does it query status
and read shared RAM.

To inspect recent raw edges after auto-stop:

```bash
sudo -E python3 hil_raw_cli.py dump --limit 32
```

To rerun analysis without recapturing:

```bash
sudo -E python3 hil_raw_cli.py analyze --min-deadtime-ns 600
```

## Expected result

For an accurately generated 20 kHz source:

```text
period                         ~ 50 us
H->L dead-time                 source/reference value
L->H dead-time                 source/reference value
overlap_count                  0
min_deadtime_violation_count   0 for a 600 ns threshold and ~700 ns source
overflow_count                 0
event_count                    configured event limit
stop_reason                    1 (event-limit auto-stop)
```

The important acceptance metric is no longer merely event ordering. Compare
the reconstructed edge deltas directly against a logic analyzer or
oscilloscope at the BBB input pins.

## RPMsg rule during precision capture

Do not repeatedly issue `status`, `ping`, `hello` or other RPMsg commands
while a precision capture is running. Firmware can service host requests so a
stuck/static-input capture remains recoverable, but doing so necessarily steals
PRU cycles from R31 polling and can create timing outliers.

For qualification runs use:

```text
CONFIG -> CLEAR -> START -> no host traffic -> event-limit auto-stop -> READ
```

## Next acceptance work

After the U pair is validated:

1. repeat 600/700/800 ns dead-time profiles;
2. repeat duty 5/25/50/75/95%;
3. compare against logic-analyzer timing distributions;
4. connect all six outputs using HPM6E00EVK or GD32H75EY-EVAL;
5. characterize maximum sustainable aggregate edge rate;
6. inspect generated PRU assembly and establish a documented fixed sampling
   latency / resolution bound.
