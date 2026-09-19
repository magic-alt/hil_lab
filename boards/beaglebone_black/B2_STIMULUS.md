# B2 PRU1 stimulus / encoder emulation

Issue: #13

B2 uses PRU1 as the deterministic digital stimulus engine while PRU0 remains the
capture engine. Linux/RPMsg is the control plane only; real-time edges stay in
PRU1.

## Firmware split

Two mutually exclusive PRU1 firmware images are provided.

### `pru1_b2`: ABZ scheduler + Hall

Pins:

| Signal | BBB pin | PRU1 direct signal |
| --- | --- | --- |
| A / Hall-U | P8_45 | R30[0] |
| B / Hall-V | P8_46 | R30[1] |
| Z / Hall-W | P8_43 | R30[2] |

ABZ forward Gray sequence:

```text
00 -> 10 -> 11 -> 01 -> 00
```

Reverse walks the same Gray states in the opposite direction.

The nominal ABZ path has already been physically validated at 60 rpm / 1000 PPR
in both directions with zero illegal transitions. The first max-rate sweep on
firmware 0x00030000 showed zero whole-period late transitions through
500 ktransition/s; 1 MHz and above exposed a control-plane START boundary.

Firmware 0x00031000 changes immediate START semantics to **ACK-before-run**:

```text
ABZ_START request
  -> validate / mark pending
  -> send RPMsg ACK
  -> fresh IEP timestamp
  -> apply initial ABZ state
  -> establish first deadline
  -> RUN
```

This prevents the RPMsg response path from consuming the first high-rate
transition period.

A bounded timestamped scheduler foundation is also included:

```text
CONFIG
  -> ARM at absolute 32-bit IEP timestamp
  -> optionally queue one future speed/direction update
  -> RUN without Linux edge timing
  -> STOP / FORCE_SAFE
```

The single queued update is intentionally a foundation for the later bounded
schedule queue. It is sufficient to qualify deterministic speed-step and
direction-reversal semantics without Linux toggling edges in real time.

Hall mode uses the same three physical outputs and the forward sequence:

```text
001 -> 101 -> 100 -> 110 -> 010 -> 011 -> 001
```

Reverse traverses the same six states in the opposite direction.

### `pru1_b2_serial`: SSI / BiSS-C / SPI-style

This alternate firmware is deployed instead of `pru1_b2`. Serial modes need
different pin directions and therefore are not concurrent with ABZ/Hall.

SSI / BiSS-C map:

| Signal | BBB pin | PRU1 direct signal |
| --- | --- | --- |
| MA / CLK | P8_45 | R31[0] input |
| SLO / DATA | P8_46 | R30[1] output |

SPI-style mode-0 map:

| Signal | BBB pin | PRU1 direct signal |
| --- | --- | --- |
| SCLK | P8_45 | R31[0] input |
| MISO | P8_46 | R30[1] output |
| CS_n | P8_43 | R31[2] input |
| MOSI | P8_44 | R31[3] input |

Current serial baseline:

- SSI: 1..32-bit MSB-first shift-out on external master clock;
- BiSS-C: configurable position width plus ERR/WARN and inverted CRC6;
- SPI-style: generic mode-0 response with MOSI capture;
- frame counter, protocol-error counter and minimum observed half-period;
- STOP / FORCE_SAFE safe-low output;
- SSI/BiSS DATA idles high only while the emulator is enabled.

BiSS-C framing implemented by this baseline:

```text
ACK(0) | START(1) | CDS(0) | POSITION | ERR | WARN | inverted CRC6
```

CRC covers POSITION + ERR + WARN using polynomial
`x^6 + x + 1` (0x43). ACK/START/CDS are excluded from the CRC calculation.

This is a protocol-development baseline, **not yet a physical timing
qualification**. In particular, real BiSS-C MA/SLO phase alignment, timeout
behavior, measured clock ceiling and differential electrical adaptation remain
hardware tests.

The generic SPI mode does not claim compatibility with a named encoder IC until
that device's actual command/register/CRC protocol is implemented.

## Build

ABZ/Hall:

```bash
cd ~/hil_lab
unset PSSP_DIR
export PRU_CGT=/usr/share/ti/cgt-pru
make bbb-b2-pru-build
```

Serial:

```bash
make bbb-b2-serial-pru-build
```

## Deploy / pinmux

ABZ/Hall:

```bash
cd ~/hil_lab/boards/beaglebone_black
sudo sh pinmux/setup_b2_abz_outputs.sh
sudo python3 scripts/pru1_ctl.py deploy firmware/pru1_b2/gen/hil_b2_pru1.out
```

SSI/BiSS:

```bash
sudo sh pinmux/setup_b2_ssi_biss.sh
sudo python3 scripts/pru1_ctl.py deploy firmware/pru1_b2_serial/gen/hil_b2_serial_pru1.out
```

SPI-style:

```bash
sudo sh pinmux/setup_b2_spi_sensor.sh
sudo python3 scripts/pru1_ctl.py deploy firmware/pru1_b2_serial/gen/hil_b2_serial_pru1.out
```

## Host control

ABZ/Hall uses:

```bash
cd boards/beaglebone_black/host
python3 hil_stim_cli.py hello
python3 hil_stim_cli.py config --rpm 60 --ppr 1000 --direction forward
python3 hil_stim_cli.py start
python3 hil_stim_cli.py status
python3 hil_stim_cli.py stop
```

Timestamped ABZ start/update foundation:

```bash
python3 hil_stim_cli.py arm --after-us 50000
python3 hil_stim_cli.py schedule --after-us 500000 --transition-hz 100000 --direction reverse
python3 hil_stim_cli.py scheduler-status
```

The schedule command is queued before the real-time run so ordinary Linux/RPMsg
latency does not control the eventual edge timestamp.

Hall baseline:

```bash
python3 hil_stim_cli.py hall-config --transition-hz 1000 --direction forward
python3 hil_stim_cli.py hall-start
python3 hil_stim_cli.py hall-status
python3 hil_stim_cli.py hall-stop
```

Serial modes use `hil_sensor_cli.py`.

Example SSI:

```bash
python3 hil_sensor_cli.py config --mode ssi --bits 24 --gap-us 2
python3 hil_sensor_cli.py data --value 0x5a3cc3
python3 hil_sensor_cli.py start
python3 hil_sensor_cli.py status
```

Example BiSS-C:

```bash
python3 hil_sensor_cli.py config --mode biss --bits 18 --gap-us 2
python3 hil_sensor_cli.py data --value 0x12345 --preview-biss-bits 18
python3 hil_sensor_cli.py start
```

Example generic SPI mode-0:

```bash
python3 hil_sensor_cli.py config --mode spi --bits 16
python3 hil_sensor_cli.py data --value 0xa55a
python3 hil_sensor_cli.py start
```

## PRU1 stack budget

PR #45 increased the B2 runtime state enough that the previous 256-byte PRU1 stack was no longer sufficient. On real BBB hardware the firmware loaded under remoteproc but failed to register the RPMsg namespace; the disassembly showed a 208-byte `main` frame before nested PSSP RPMsg calls. Increasing the linker stack from `0x100` to the hardware-qualified `0x400` restored `/dev/rpmsg_pru31` immediately.

Both B2 PRU1 firmware images therefore reserve a 1 KiB stack. Static gates prevent accidental regression to the old 256-byte budget. Future B2 growth should re-check generated disassembly/map depth before reducing this allocation.

## Timing and rollover

All B2 firmware uses the shared PRU-ICSS IEP counter:

```text
tick_hz      = 200 MHz
tick         = 5 ns
counter_bits = 32
```

Absolute scheduled timestamps use unsigned 32-bit IEP ticks and wrap-safe signed
deadline comparisons. A requested absolute timestamp must be in the future by
less than half the counter range.

## Safety / electrical boundary

Raw BBB headers are 3.3 V single-ended logic.

- Do not connect RS-422/differential SSI/BiSS directly to BBB pins.
- Use a reviewed differential receiver/driver or level-shift/protection adapter.
- P8_43..P8_46 overlap the BBB LCD/HDMI pin group; run headless and confirm
  pinmux ownership.
- STOP/FORCE_SAFE drives B2 outputs to the documented safe-low state.

## Remaining #13 hardware qualification

Development can proceed before these tests, but #13 is not complete until the
relevant physical evidence exists:

- repeat ABZ max-rate sweep after ACK-before-run;
- timestamped ABZ start/speed-step/reversal timing;
- real servo MCU QEP position/direction;
- Hall six-step waveform;
- SSI/BiSS-C frame timing and measured clock ceiling;
- BiSS-C CRC/status/timeout fault cases;
- generic SPI baseline and at least one selected real encoder IC protocol;
- host-loss/PRU-stop safe-output behavior.
