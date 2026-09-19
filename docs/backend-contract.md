# HIL Backend Contract

This contract defines backend-neutral semantics used by host software and pytest.

## Core rules

1. Tests request capabilities rather than board models.
2. Deterministic behavior executes in FPGA PL or PRU.
3. Raw hardware timestamps remain available.
4. Unsupported capabilities are explicit.
5. Safe state is a backend-local requirement.
6. Infrastructure failure is distinct from DUT failure.

The executable contract starts in host/hil/core.py. architecture/manifest.json is the machine-readable registry checked by CI.

## Required backend identity

Every deterministic backend reports:

- backend_type;
- hardware_revision;
- firmware_revision / bitstream revision;
- api_version;
- capability set;
- tick_hz;
- counter_bits;
- health/error counters.

Every backend must provide timebase and force_safe.

## Capability registry

Initial Architecture v2 capabilities:

- timebase
- force_safe
- pwm_capture
- pwm_generator
- pwm_complementary_monitor
- abz_generator
- abz_capture
- ssi_sensor_emulator
- ssi_sensor_capture
- biss_sensor_emulator
- spi_sensor_emulator
- dio_scheduler
- fault_injection
- dac_feedback
- pmsm_plant_lite
- pmsm_plant
- dual_inertia_plant

A capability name may be added only with defined semantics and a conformance test path. Plain SSI must not be reported as BiSS-C.

## Timestamp semantics

A Timestamp contains ticks, tick_hz and counter_bits.

seconds = ticks / tick_hz is a host conversion only. Rollover must be handled explicitly by the transport/backend and never hidden as ambiguous wall-clock time.

## PWM measurement

pwm_capture results identify channel, measurement sequence, period/high/low ticks and validity/overflow state. Implementations may expose additional edge timestamps.

pwm_complementary_monitor additionally reports both dead-time directions plus overlap/minimum-dead-time fault state.

## ABZ

abz_generator configuration includes enable, transition period, direction, initial state, index behavior and acknowledged/apply timing. Electrical voltage and differential signaling belong to the adapter, not this API.

## Deterministic events

dio_scheduler accepts an event id, target hardware timestamp, mask and value. Evidence should retain requested and actual apply timestamps plus late/overflow/error flags when implemented.

## Scenario contract

host/hil/scenario.py provides the first versioned scenario parser. A scenario declares required_capabilities and ordered at_ticks actions.

The host validates the capability set first. Backend-specific executors may reject an action that exceeds queue depth/rate/timing limits. Linux must not emulate a rejected real-time action with sleeps.

## Controller services are not backend capabilities

Raspberry Pi services such as IgH, SOEM, SocketCAN, CANopen, labgrid and optional ROS2 are controller services. They are intentionally not mixed into the deterministic backend capability enum.

## Error model

Host code distinguishes:

- UnsupportedCapability;
- InvalidConfiguration;
- InfrastructureError;
- backend overflow/data loss;
- DUT assertion failure.

G5/D2 unattended Servo CI must preserve this distinction in reports and cleanup.
