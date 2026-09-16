# AXU2CGB G0 bring-up and qualification

This procedure qualifies the **digital signal-level** HIL path. It must not be
used to connect the FPGA directly to a 48 V DC bus, MOSFET switch node, motor
phase, brake power output, or other high-energy node.

## 1. Pre-power checks

Record:

- AXU2CGB PCB/core-board revision and serial label;
- Vivado version;
- git commit and bitstream SHA256;
- oscilloscope / logic analyzer model;
- DUT-adapter revision.

Verify continuity from the planned J12/J15 pins to the adapter before plugging
in the servo controller.

## 2. Clock sanity

The project constrains AB11 as a 25 MHz input and generates 100 MHz internally.
The project follows the ALINX factory XDC (`LVCMOS33`) even though one version
of the user manual describes the PL clock level as +1.8 V. Before timing
qualification, verify the actual board revision and measured clock waveform.

Expected HIL tick at 100 MHz:

```text
1 tick = 10 ns
20 kHz PWM period = 50 us = 5000 ticks
600 ns dead time = 60 ticks
700 ns dead time = 70 ticks
800 ns dead time = 80 ticks
```

The G0 top defaults to a 500 ns (50 tick) minimum-dead-time threshold; product
qualification should override the threshold to the DUT specification.

## 3. FPGA-only connector test

Do not connect a servo DUT yet.

1. Program `axu2cgb_hil.bit`.
2. Confirm clock-lock status.
3. Drive `HIL_ENABLE=1`.
4. Drive `FORCE_SAFE=0`.
5. Drive `TEST_PATTERN_ENABLE=1`.
6. Measure J15 DIO[15:0] and confirm `16'hA55A`.
7. Return `FORCE_SAFE=1`; all DUT-facing outputs must return low.

This proves the FPGA, constraints, header orientation and basic output path
before introducing the DUT.

## 4. PWM capture qualification

Use a function generator or known-safe 3.3 V source first, then the DUT PWM
logic output.

Test matrix:

| Case | Frequency | Duty | Dead time | Expected |
|---|---:|---:|---:|---|
| nominal | 20 kHz | 50% | 700 ns | no fault |
| min valid | 20 kHz | variable | 600 ns | no fault for 600 ns limit |
| below limit | 20 kHz | variable | 400 ns | dead-time fault |
| overlap | 20 kHz | N/A | negative | shoot-through fault |
| missing phase | 20 kHz | N/A | N/A | no new period on missing input |

Compare measured period/dead time with the oscilloscope. At 100 MHz, expected
quantization is 10 ns plus asynchronous synchronizer edge uncertainty.

## 5. Encoder and SPI qualification

ABZ:

- verify A/B Gray sequence in both directions;
- verify Z index once per configured revolution;
- verify outputs are low during FORCE_SAFE;
- test at low and high edge rates before connecting the real MCU.

SPI:

- G0 implements mode 0 and a fixed 24-bit frame;
- start at <= 1 MHz for bring-up, then raise SCLK while checking margins;
- the 100 MHz HIL clock is intended to oversample common servo SPI rates;
- protocol-specific CRC/command handling remains a follow-on task.

## 6. Evidence to attach to issue #1

Attach or record:

- Vivado timing summary and DRC result;
- pin-map checker result;
- 25 MHz reference / 100 MHz derived-clock evidence;
- J15 `0xA55A` connector pattern capture;
- 20 kHz PWM/dead-time comparison table;
- ABZ waveform;
- SPI transaction capture;
- exact DUT hardware/firmware revision.

Only after these are complete should G0 be treated as physically qualified and
G1 DAC evaluation become the primary bench-development gate.
