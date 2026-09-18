# Architecture — Multi-Backend Signal-Level Servo HIL

## Objective

`hil_lab` validates servo-controller firmware while keeping high-energy inverter/motor behavior outside the first-generation bench.

The architecture now separates:

- **host/test semantics**;
- **real-time backend implementations**;
- **electrical DUT adaptation**.

This permits a ZU2CG FPGA Full-HIL backend, a Zynq-7010 FPGA-Lite backend and a BeagleBone Black PRU Digital-HIL backend to coexist without forcing any platform into another backend's implementation model.

## System layering

```text
+-------------------------------------------------------------+
| Host / pytest / future Servo CI                             |
| test intent, limits, reports, DUT lifecycle                 |
+-----------------------------+-------------------------------+
                              |
                              | common backend contract
                              | capabilities + commands + events
                              v
              +---------------+----------------+
              |                                |
              v                                v
+-----------------------------+   +-----------------------------+
| ZU2CG / AXU2CGB backend     |   | BBB / AM3358 PRU backend   |
|                             |   |                             |
| FPGA timebase               |   | PRU-local timestamp         |
| PWM/dead-time capture       |   | PWM/dead-time capture       |
| ABZ/SPI emulation           |   | ABZ generation              |
| deterministic DIO           |   | deterministic fault GPIO    |
| DAC/analog feedback         |   | digital-only first scope    |
| PMSM plant (G2+)            |   |                             |
+--------------+--------------+   +--------------+--------------+
               |                                 |
               +---------------+-----------------+
                               |
                               v
+-------------------------------------------------------------+
| Protected HIL I/O / DUT adapter                             |
| level shift / differential drivers / isolation / clamps     |
| analog switches / relays only where reviewed                |
+-----------------------------+-------------------------------+
                              |
                              v
+-------------------------------------------------------------+
| Servo controller DUT: GD32/HPM MCU + low-voltage interfaces |
+-------------------------------------------------------------+
```

## Control plane vs real-time data plane

Linux owns the **control plane**:

- configure tests;
- load parameters;
- arm events;
- collect measurements;
- write reports;
- manage DUT lifecycle.

FPGA PL or PRU owns the **real-time data plane**:

- edge capture;
- interval measurement;
- encoder transition generation;
- timestamped GPIO events;
- other deterministic operations.

A backend must never implement a nominally deterministic capability with ordinary Linux userspace timing merely to satisfy the common API.

## Timing contract

The common contract represents hardware time as:

- a raw monotonic tick counter;
- a declared tick frequency;
- explicit counter width/rollover behavior.

Host software may convert ticks to SI time, but raw timing evidence must remain available.

The ZU2CG G0 reference uses a 100 MHz FPGA clock (10 ns/tick). The AX7010 FPGA-Lite target also derives a 100 MHz HIL clock from its 50 MHz PL oscillator.

The BBB PRU time source is selected and physically characterized in B0 (#11). Its exact timer implementation must not be assumed by host tests before B0 freezes it.

Cross-backend tests compare semantic quantities and declared tolerances; they do not assume identical quantization.

## ZU2CG backend

The FPGA backend remains the Full-HIL reference.

Reusable blocks include:

- `hil_timebase`;
- `pwm_capture`;
- `pwm_complementary_monitor`;
- `abz_encoder_emulator`;
- `spi_encoder_emulator`;
- `dio_event_scheduler`.

Board-specific clocking, pins and future analog interfaces stay under `boards/zu2cg/`.

G1+ extends this backend with deterministic DAC output, then PMSM and robotic-joint plant models.

## Zynq-7010 FPGA-Lite backend

The XC7Z010 lane fills the gap between software-programmable PRU Digital-HIL
and the larger ZU2CG Full-HIL fabric.

The first board target is ALINX AX7010 because it exposes two 34-I/O PL
expansion headers and a dedicated 50 MHz PL clock. Board-specific integration
stays under `boards/zynq7010/`; reusable PWM/encoder/motor blocks stay under
the root `rtl/` hierarchy.

Initial responsibilities:

- deterministic complementary PWM generation plus parallel capture;
- ABZ generation and capture;
- SSI/SPI-style synchronous encoder emulation/acquisition;
- deterministic digital faults;
- a Q16.16 fixed-step single-motor PMSM-lite plant;
- later AXI-Lite/BRAM control from the Cortex-A9 PS.

The PS/Linux side is a control plane only. PWM edges, encoder timing and motor
model stepping remain in PL.

Zynq-7010 does not replace the ZU2CG backend for high-channel-count ADC/DAC,
multi-axis models, dual-inertia joint dynamics or final Full-HIL expansion.

## BBB PRU backend

BBB is a companion backend optimized for fast digital servo-firmware testing.

Initial responsibilities:

- B0: PRU lifecycle/transport/timebase/safe-state;
- B1: PWM and dead-time capture;
- B2: ABZ output;
- B3: deterministic digital fault/stimulus scheduling.

A reference partition may use one PRU primarily for capture and the other primarily for generation/events, but B0 measurements decide the final partition. Do not freeze the split before resource/timing characterization.

BBB does not initially implement:

- analog sensor synthesis;
- PMSM plant execution;
- custom ADC/DAC HIL;
- a replacement for G2/G3/G6.

## Backend capability model

See `docs/backend-contract.md`.

Tests should request capabilities such as PWM capture or ABZ generation. A backend that does not support a required capability must return an explicit unsupported result so pytest can skip/fail with a clear reason.

## Communications boundary

CAN/CAN FD, RS-485 and EtherCAT remain outside the reusable real-time cores until physical/transceiver ownership is fixed.

An external communications host can participate in a HIL scenario. For example, a Raspberry Pi running an EtherCAT master may command the servo DUT while ZU2CG/BBB observes or injects signal-level behavior. This does not require an EtherCAT master implementation inside FPGA PL or PRU.

## Safety invariant

Every backend must have a local safe state independent of host responsiveness.

Examples:

- disable external analog-output enable;
- drive encoder/fault outputs to documented benign states;
- clear scheduled events on reset unless explicitly persisted;
- use a watchdog for host-controlled potentially active stimulus.

High-energy power nodes remain out of scope.
