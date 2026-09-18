# HIL Backend Contract

This document defines backend-neutral semantics for host software and pytest.

It is intentionally smaller than any one hardware backend.

## Design principles

1. Tests declare required capabilities.
2. Backends expose hardware time explicitly.
3. Deterministic operations execute in FPGA PL or PRU, not Linux timing loops.
4. Unsupported capabilities are explicit.
5. Safe-state behavior is part of the contract.
6. Raw measurement evidence is retained alongside converted engineering units.

## Required backend metadata

Every backend should expose:

- backend type: e.g. `zynq_axu2cgb`, `zynq7010_ax7010` or `bbb_pru`;
- hardware revision;
- FPGA bitstream / PRU firmware revision;
- protocol/API version;
- capability set;
- timestamp frequency;
- timestamp counter width;
- health/error counters.

## Initial capabilities

Suggested capability identifiers:

- `timebase`
- `pwm_capture`
- `pwm_generator`
- `pwm_complementary_monitor`
- `abz_generator`
- `abz_capture`
- `ssi_sensor_emulator`
- `ssi_sensor_capture`
- `spi_sensor_emulator`
- `dio_scheduler`
- `pmsm_plant_lite`
- `dac_feedback`
- `pmsm_plant`

Names may evolve before B4 freezes the Python API, but tests must not branch on board model where a capability check is sufficient.

## Timestamp semantics

A hardware timestamp is represented by:

```text
ticks
tick_hz
counter_bits
```

Host conversion:

```text
seconds = ticks / tick_hz
```

Rollover handling must be explicit. Backends must not silently convert a wrapping hardware counter into ambiguous host wall-clock time.

## PWM measurement semantics

Where `pwm_capture` is supported, a sample should identify:

- channel;
- measurement sequence;
- rising/falling edge timestamp where available;
- period ticks;
- high ticks;
- low ticks;
- validity/overflow flags.

Where `pwm_complementary_monitor` is supported, results additionally expose:

- high->low dead-time ticks;
- low->high dead-time ticks;
- overlap/shoot-through-command latch;
- minimum-dead-time violation latch.

## ABZ generator semantics

Where `abz_generator` is supported, configuration should cover:

- enable;
- transition/step period;
- direction;
- initial phase/state;
- index interval;
- index width;
- apply timestamp or acknowledged activation timestamp.

Electrical voltage/differential signaling is not part of this logical contract.

## Deterministic DIO scheduler

Where `dio_scheduler` is supported, an event contains:

- requested hardware timestamp;
- output mask;
- output value;
- event identifier.

Execution evidence should retain:

- requested timestamp;
- actual timestamp;
- resulting state;
- late/overflow/error flags.

## Safe-state semantics

Every backend must support a local `force_safe` or equivalent operation and define what happens on:

- host disconnect;
- backend firmware stop/reset;
- board reset;
- watchdog expiry.

Potentially active stimulus must not depend on Linux cleanup code to become safe.

## Error model

Host code should distinguish:

- unsupported capability;
- invalid configuration;
- backend/transport infrastructure failure;
- measurement overflow/data loss;
- DUT test failure.

This distinction is required before unattended G5 Servo CI is considered complete.


## FPGA-Lite capability boundary

The Zynq-7010/AX7010 backend may expose `pmsm_plant_lite` separately from
the ZU2CG `pmsm_plant` capability. Tests must not assume those models have
the same numerical fidelity, analog-I/O bandwidth or multi-axis capacity.

Encoder protocols are also capability-specific. Plain SSI support must not be
reported as BiSS-C support unless BiSS framing, CRC and timing semantics are
implemented and qualified.
