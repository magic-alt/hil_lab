# G1 DAC evaluation path: 2x EVAL-AD3542R

G1 validates the analog feedback timing architecture before a custom HIL analog
PCB is designed.

## Reference topology

Use two EVAL-AD3542R boards in parallel for the first four sensor channels:

| DAC board | CH0 | CH1 |
|---|---|---|
| A | Ia feedback | Ib feedback |
| B | Ic feedback | Vbus feedback |

Both boards share `CS_n`, `SCLK`, `RESET_n` and `LDAC_n`. Each board gets an
independent SDIO0/MOSI stream. Corresponding channels on the two boards update
in parallel; within each AD3542R, CH1 and CH0 are serialized and therefore have
a deterministic 16-SCLK inter-channel skew in this first evaluation mode.

## Why AD3542R

The AD3542R is a dual-channel, 16-bit voltage-output precision DAC intended for
fast control/instrumentation. The device supports fast streaming modes well
above the G1 >=1 MSPS target, and the evaluation board exposes its digital
interface at P5 for an external controller.

G1 selects the 0 V to 5 V span for both channels (`CH0_CH1_OUTPUT_RANGE =
0x11`). HIL sensor voltages are limited in software/adapter hardware to the DUT
safe range (normally 0 V to 3.3 V).

For an ideal 0 V to 5 V transfer:

```text
DAC_code = round(clamp(Vcmd, 0, 5) / 5 * 65535)
```

Calibration later replaces the ideal slope/offset with measured per-channel
coefficients.

## Streaming protocol used by the FPGA

The G1 RTL uses the AD3542R power-up 7-bit instruction format and descending
DAC-register addressing:

1. write `STREAM_MODE (0x0E) = 0x04`;
2. write `TRANSFER_REGISTER (0x0F) = 0x04`;
3. write `CH0_CH1_OUTPUT_RANGE (0x19) = 0x11`;
4. assert CS and issue write address `0x2C` (CH1 DAC MSB);
5. continuously send four bytes per board:
   `CH1_MSB, CH1_LSB, CH0_MSB, CH0_LSB`.

With a 100 MHz FPGA clock, the RTL toggles SCLK each FPGA cycle, generating a
50 MHz SPI clock. Once the one-time instruction byte is complete, a 32-bit
sample group takes 640 ns, or 1.5625 million four-channel sample vectors per
second because the two boards stream in parallel. At 50 MHz, the CH1-to-CH0
update skew inside each DAC is 320 ns. G1 measures whether that skew is
acceptable for the later PMSM loop; if not, G2 will move to a shared-LDAC/input-
register or dual-SPI update strategy.

## Required level-shifter interposer

Do **not** wire AXU2CGB J15 directly to EVAL-AD3542R P5. The AXU2CGB expansion
headers are 3.3 V logic, while AD3542R VLOGIC is 1.1 V to 1.9 V.

The G1 interposer shall provide:

- 3.3 V -> 1.8 V translation for CS, SCLK, SDIO0_A, SDIO0_B, RESET and LDAC;
  `SN74AXC8T245` is the reference translator candidate because its dual rails
  cover 1.8 V/3.3 V and its specified data-rate margin is well above the 50 MHz
  SPI path;
- optional 1.8 V -> 3.3 V paths for SDO/ALERT readback;
- local decoupling and ground reference;
- series damping footprints on high-speed digital lines;
- an independent analog-output enable/switch path driven by
  `dac_output_enable`;
- connectors that make it impossible to confuse DAC outputs with FPGA GPIO.

SPI zero-code streaming is **not** the independent safety mechanism. The
external analog switch/clamp path must force a defined DUT-safe state when HIL
output enable is low or FPGA power is absent.

## Calibration vectors

`dac_eval_pattern_generator` rotates four ideal 0-5 V codes across all four
channels so every channel sees each qualification point exactly once:

- 0.25 V: `0x0CCD`
- 1.65 V: `0x547B`
- 3.00 V: `0x9999`
- 3.30 V: `0xA8F5`

This simultaneously checks channel routing and gives gain/offset data at useful
servo-ADC operating points.

## G1 qualification measurements

1. Confirm all four outputs can be updated deterministically.
2. Measure SPI clock, CS behavior and stream byte ordering.
3. Measure command-to-DAC-output latency and 0.1% settling with an oscilloscope.
4. Sweep 0.25 V, 1.65 V, 3.0 V and 3.3 V target levels and record gain/offset.
5. Measure the 320 ns serialized channel skew and decide whether G2 needs a
   simultaneous-update mode.
6. Feed the four outputs into a safe ADC/load fixture before connecting a servo.
7. Connect Ia/Ib/Ic/Vbus injection nodes on a protected DUT adapter.
8. Verify `dac_output_enable=0` produces the hardware-defined safe state.

Custom 8-channel ADC/DAC PCB work remains G3 and must use the measured G1
latency/noise/settling data as its requirements baseline.
