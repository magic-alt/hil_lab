# Signal-Level I/O Contract

This document defines the logical FPGA boundary. Electrical levels at connectors are determined by the board-specific adapter and must not be inferred from these RTL ports.

## PWM inputs

Logical signals:

- `pwm_high[2:0]` — U/V/W high-side commands;
- `pwm_low[2:0]` — U/V/W low-side commands.

Requirements:

- treat DUT PWM as asynchronous to the FPGA reference clock;
- level-shift and protect before the FPGA pin;
- do not connect to MOSFET drain/source nodes or motor phases;
- gate-driver logic outputs may require isolation depending on grounding.

G0 measurements are in FPGA clock ticks.

## ABZ encoder outputs

Logical outputs:

- `enc_a`;
- `enc_b`;
- `enc_z`.

Board adapter responsibilities:

- match DUT I/O voltage;
- provide differential line drivers if the DUT expects RS-422-style A/A-, B/B-, Z/Z-;
- define power-off/high-impedance behavior where required.

## SPI encoder/sensor interface

Logical signals:

- DUT -> HIL: `spi_sclk`, `spi_cs_n`, `spi_mosi`;
- HIL -> DUT: `spi_miso`.

G0 supports SPI mode 0 at the core level. Protocol-specific frame formatting and CRC generation are intentionally separated from the serial shifter; `spi_frame_data` provides the frame to transmit and `spi_fault_flip_mask` supports deterministic bit corruption.

## Digital event outputs

`dio_out[15:0]` is a logical stimulus/fault-control bus. Board-specific circuitry determines whether a channel is push-pull, open-drain, isolated, relay-controlled or unused.

## Future analog outputs

Planned DAC outputs include:

- Ia / Ib / Ic feedback;
- DC-bus sense;
- temperature;
- torque sensor;
- other low-voltage analog commands.

The initial DUT-facing target is typically 0–3.3 V, but the adapter must follow the actual DUT ADC network. The custom analog board is a later roadmap gate and is not part of G0 RTL.
