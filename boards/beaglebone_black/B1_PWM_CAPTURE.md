# B1 PRU PWM capture and complementary dead-time monitor

Issue: #12

B1 builds on the validated B0 remoteproc/RPMsg/timebase baseline and moves all
timing-critical PWM work into PRU0.

## Architecture

```text
DUT six PWM logic signals
        |
        v
PRU0 direct R31 inputs
        |
single __R31 read per hot-loop iteration
        |
logical 6-bit bitmap
        |
changed?
  | no ----------------------> next sample
  |
 yes
  |
IEP timestamp
  |
capture core
  |-- period/high/low per channel
  |-- H->L / L->H complementary dead-time
  |-- overlap/shoot-through-command latch
  |-- min-dead-time violation latch
  |-- counters
  '-- 128-entry recent-edge ring
        |
PRUSS shared RAM @ physical 0x4A310000
        |
Linux /dev/mem snapshot reader
```

RPMsg is control plane only. It configures, starts/stops and queries status.
Individual PWM edges never generate one RPMsg each.

## First physical pin map

The first BBB B1 build uses six direct PRU0 inputs:

| Logical | BBB pin | PRU input |
| --- | --- | --- |
| UH | P9_29 | R31[1] |
| UL | P9_30 | R31[2] |
| VH | P9_28 | R31[3] |
| VL | P9_27 | R31[5] |
| WH | P8_16 | R31[14] |
| WL | P8_15 | R31[15] |

Configure:

```bash
cd ~/hil_lab/boards/beaglebone_black
sudo sh ./pinmux/setup_b1_pwm_inputs.sh
```

This map avoids P9_25 and P9_41/P9_42 for the first bench.

## Shared-memory ABI

AM335x PRUSS shared RAM is 12 KiB at physical `0x4A310000`. B1 places one
`struct hil_pwm_shared` at the beginning of that memory.

The current ABI is 2416 bytes:

- header/health/control state;
- six channel snapshots;
- three complementary-pair snapshots;
- 128 recent edge records.

The writer uses an even/odd `seq_lock`. Linux retries a snapshot when it sees
an odd or changing sequence.

## Measurement semantics

For every channel:

- period = current rise - previous rise;
- high time = fall - previous rise;
- low time = rise - previous fall.

For each complementary pair:

- high->low dead-time = low rise - high fall;
- low->high dead-time = high rise - low fall;
- a same-sample fall/rise pair produces 0 ticks;
- simultaneous high+low assertion latches overlap;
- valid dead-time below the configured minimum latches a violation.

32-bit IEP subtraction intentionally uses unsigned modulo arithmetic. At the
B1 target rates all expected PWM/dead-time intervals are many orders below the
~21.47 s 32-bit IEP rollover.

## Host commands

B1 extends the fixed 32-byte RPMsg control protocol with:

```text
CAPTURE_CONFIG
CAPTURE_START
CAPTURE_STOP
CAPTURE_CLEAR
CAPTURE_STATUS
```

Example:

```bash
cd ~/hil_lab/boards/beaglebone_black/host

python3 hil_pwm_cli.py config --min-deadtime-ns 700
python3 hil_pwm_cli.py clear
python3 hil_pwm_cli.py start
python3 hil_pwm_cli.py status

sudo -E python3 hil_pwm_cli.py snapshot --ring-limit 16

python3 hil_pwm_cli.py stop
```

`snapshot` needs access to `/dev/mem`; on the current BBB this normally
requires root.

## Build

Software/core gates:

```bash
make bbb-check
```

Real PRU build:

```bash
unset PSSP_DIR
export PRU_CGT=/usr/share/ti/cgt-pru

make bbb-b1-pru-env
make bbb-b1-pru-build
```

Expected output:

```text
boards/beaglebone_black/firmware/pru0_b1/gen/hil_b1_pru0.out
```

Deploy after B0 physical acceptance is complete:

```bash
cd boards/beaglebone_black
sudo python3 scripts/pru0_ctl.py deploy firmware/pru0_b1/gen/hil_b1_pru0.out
```

## Current performance intent

B0 measured a deterministic R30->jumper->R31 observation latency of 49 IEP
ticks (245 ns) over 1000 persistent-loopback samples. B1 does not assume the
same figure for six-input capture. The six-channel hot loop must be
characterized independently, including maximum edge rate and compiler output.

The first implementation is semantics-first C. Before claiming the final B1
timing bound, inspect generated PRU assembly and optimize/unroll the hot loop if
required.

## STM32F429I-DISC1 stimulus source

The first physical B1 input source is now provided in:

```text
boards/stm32f429i_disc1/
```

It uses TIM8 complementary outputs:

```text
PC6 / TIM8_CH1  / P1-57 -> BBB P9_29 / UH
PA5 / TIM8_CH1N / P2-21 -> BBB P9_30 / UL
GND                         BBB GND
```

Default waveform:

```text
20 kHz
50% reference duty
700 ns dead-time
3.3 V logic
```

Open the native Keil project:

```text
boards/stm32f429i_disc1/MDK-ARM/hil_pwm_stimulus.uvprojx
```

Use the uVision Target selector to switch between 600/700/800 ns dead-time and
5/25/50/75/95% duty configurations. See
`boards/stm32f429i_disc1/README.md` for the full Keil workflow.

## Physical verification sequence

1. Use a logic-level 20 kHz complementary PWM source.
2. Start with one pair U_H/U_L.
3. Sweep duty 5%, 25%, 50%, 75%, 95%.
4. Sweep dead-time around 600/700/800 ns.
5. Add V and W pairs.
6. Run all six channels continuously.
7. Compare period, duty and dead-time against a scope/logic analyzer.
8. Deliberately command overlap and sub-threshold dead-time.
9. Run long-duration edge-count consistency testing.
10. Characterize the maximum sustainable input edge rate.

Do not connect raw BBB pins directly to a servo gate-driver power domain. Use
3.3 V compatible logic or a reviewed buffer/level-shifter adapter.
