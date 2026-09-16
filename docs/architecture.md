# Architecture — Generation 1 Signal-Level Controller HIL

## Objective

Generation 1 validates servo-controller firmware while the real inverter power stage and motor are absent from the control loop.

The platform observes digital commands from the DUT and emulates low-voltage feedback interfaces. It is intentionally not a power HIL.

## Layering

```text
Host / future test orchestrator
        |
        | future Ethernet / RPC / register control
        v
+---------------------------------------+
| ZU2CG / Zynq programmable logic       |
|                                       |
|  timebase                             |
|      |                                |
|      +--> PWM capture / deadtime      |
|      +--> encoder emulation           |
|      +--> SPI sensor emulation        |
|      +--> deterministic DIO events    |
+------------------+--------------------+
                   |
                   | FPGA-safe digital boundary
                   v
+---------------------------------------+
| HIL I/O / DUT adapter                 |
| level shift / isolation / clamp       |
| future DAC + ADC                      |
+------------------+--------------------+
                   |
                   v
+---------------------------------------+
| Servo controller DUT                  |
| MCU / gate-driver logic / comms       |
+---------------------------------------+
```

## Timing model

The reusable G0 RTL uses one FPGA reference clock. External DUT signals are asynchronous to this clock and are synchronized before ordinary edge processing.

This gives deterministic sampled measurements, not analog-time metrology. At a 100 MHz reference clock, one timestamp tick is 10 ns. Synchronizer latency shifts absolute edge timestamps, while differences between equally synchronized edges retain clock-tick measurement resolution.

For later sub-clock or very-high-precision timing, dedicated input capture resources or vendor-specific primitives may be introduced under `boards/` without changing the core measurement interface.

## Modules

### `hil_timebase`

Free-running timestamp counter shared by measurement and event blocks.

### `pwm_capture`

Captures rising/falling edges of one asynchronous PWM input and reports:

- period ticks;
- high ticks;
- low ticks;
- edge timestamps;
- one-cycle valid pulses.

### `pwm_complementary_monitor`

Monitors a high/low complementary pair and reports both dead-time directions. It latches:

- high-and-low simultaneous assertion;
- dead-time below a programmable minimum.

### `abz_encoder_emulator`

Generates deterministic quadrature A/B transitions and an index pulse from a configured step period/direction.

### `spi_encoder_emulator`

G0 SPI mode-0 slave emulator. It serializes a supplied frame MSB-first and can XOR a deterministic fault mask into the transmitted frame.

The FPGA reference clock must substantially oversample SCLK. Exact supported SCLK limits are a board-integration validation item.

### `dio_event_scheduler`

Holds one pending event. At or after a specified FPGA timestamp, a masked set of digital outputs is updated atomically.

This is the seed for later fault-injection and deterministic stimulus sequencing.

## Explicit non-goals of G0

- PMSM equations in RTL;
- analog sensor synthesis;
- high-energy short/open fault injection;
- EtherCAT master implementation inside the reusable core;
- vendor-specific AXI or PS software as a prerequisite for core simulation.
