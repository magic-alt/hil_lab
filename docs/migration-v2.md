# Architecture v2 Migration Plan

## Why this is incremental

The current rtl/time, rtl/pwm, rtl/encoder, rtl/io, rtl/motor and rtl/dac paths are already referenced by Makefile targets, Vivado Tcl and physically qualified BBB/FPGA work. A single repository-wide move would create review noise and hardware-regression risk without improving behavior.

Architecture v2 therefore creates the target taxonomy first and migrates one coherent module family per PR.

## Phase 0 — this refactor

- create machine-readable architecture manifest and CI gate;
- create backend-neutral Python contract and versioned scenario parser;
- create target rtl/pru/fieldbus/host/tests/lab directory skeleton;
- add Raspberry Pi controller Track D;
- keep all current RTL/PRU build paths working.

## Phase 1 — RTL taxonomy

Recommended order:

1. [x] rtl/time/hil_timebase.v -> rtl/common/timebase/
2. [x] capture-only PWM/encoder blocks -> rtl/capture/
3. [x] PWM/ABZ/SSI/SPI generators -> rtl/generator/
4. [ ] rtl/io/dio_event_scheduler.v -> rtl/scenario/
5. [ ] rtl/motor plant models -> rtl/plant/
6. [ ] reusable fault latches/queues/snapshot/FIFO helpers -> rtl/common/{fault,snapshot,fifo}/

Each move updates root Makefile, board Vivado Tcl, policy checks and simulations in the same PR. Module names should remain unchanged unless behavior changes.

Do not keep duplicate canonical and legacy RTL files. During migration the old path is authoritative until a specific family is moved.

## Phase 2 — common backend implementations

- ZU2CG transport/AXI backend;
- AX7010 PS/AXI backend;
- BBB PRU adapter wrapping the already qualified command/snapshot ABI;
- conformance tests against overlapping capabilities.

The common API is semantic; it does not force identical transports.

## Phase 3 — controller and fieldbus

- D0 Raspberry Pi controller service;
- D1 IgH/SOEM and SocketCAN/CANopen adapters;
- scenario-level fieldbus actions correlated with backend hardware evidence;
- no deterministic Linux GPIO fallback.

## Phase 4 — lab automation

- labgrid resources and reservation;
- DUT power/reset/flash;
- unattended pytest hardware suites;
- artifacts and safe cleanup;
- optional ROS2 and observability after the evidence model is stable.

## Review rule

A refactor PR is accepted only if it preserves current verification gates or replaces them with stronger equivalent gates. Hardware-validation status must never be changed from pending to passed by a directory-only change.

## Phase 1-2 completion invariant

The following legacy source paths are now forbidden by `architecture/manifest.json` and `tools/architecture_check.py`:

- `rtl/time/hil_timebase.v`;
- `rtl/pwm/pwm_capture.v`;
- `rtl/pwm/pwm_complementary_monitor.v`;
- `rtl/encoder/abz_encoder_capture.v`;
- `rtl/encoder/ssi_encoder_master_capture.v`.

Module names and behavior are unchanged; this is a source-taxonomy migration only.

## Phase 3 completion invariant

The legacy `rtl/pwm/` and `rtl/encoder/` trees are now forbidden by the architecture gate. Their generator/emulator sources moved without module or logic changes to `rtl/generator/`.
