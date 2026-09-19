# Scenario RTL

Canonical Architecture v2 home for deterministic event execution, triggers and signal-level fault primitives.

Current modules:

- `dio_event_scheduler.v` — original single timestamped masked-DIO scheduler, retained for compatibility;
- `hil_event_queue.v` — bounded FIFO for nondecreasing hardware-timestamped events with overflow/order-error latches;
- `dio_scenario_engine.v` — queued masked-DIO execution with requested/actual timestamp and lateness evidence;
- `trigger_engine.v` — synchronized rising/falling external-trigger capture with hardware timestamp/count;
- `digital_fault_injector.v` — deterministic stuck-low/stuck-high logical override with FORCE_SAFE priority.

Electrical open-circuit/short injection remains the responsibility of reviewed adapter hardware.
