# Verification Strategy

Verification is split into backend-specific implementation gates and backend-neutral conformance tests.

## ZU2CG / FPGA gates

`make verify` currently performs:

1. `policy` — RTL-language and repository rules;
2. `compile` — reusable-top elaboration with Icarus Verilog;
3. `test` — self-checking RTL simulations;
4. `lint` — Verilator lint;
5. board-specific checks added by the AXU2CGB integration.

Current simulations cover:

- PWM period/high/low measurement;
- complementary dead-time and fault latching;
- ABZ transition/index generation;
- SPI mode-0 serialization and deterministic bit corruption;
- timestamped masked DIO updates.

These gates remain mandatory while BBB work is added.

## BBB / PRU gates

B0-B3 should introduce a separate verification ladder:

```text
PRU build/static checks
    -> host/PRU version + capability handshake
    -> BBB header loopback
    -> logic-analyzer timing qualification
    -> protected adapter
    -> real servo DUT
```

Minimum evidence:

- PRU firmware SHA/version;
- timestamp clock/tick metadata;
- safe-state behavior on boot/reset/PRU stop/host loss;
- measured event timing;
- event-loss/overflow counters;
- maximum sustained input/output rate.

## Cross-backend conformance

B4 (#15) adds common tests for overlapping semantics.

Expected early matrix:

| Capability | ZU2CG | BBB PRU |
|---|---:|---:|
| timestamp metadata | yes | B0 |
| PWM capture | yes | B1 |
| complementary dead-time | yes | B1 |
| ABZ generation | yes | B2 |
| deterministic digital events | yes | B3 |
| SPI sensor emulation | yes | later/optional |
| DAC analog feedback | G1 | no |
| PMSM plant | G2 | no |

A conformance test may use different timing tolerances per backend, but the logical meaning of measurements/events must remain consistent.

## Hardware validation ladder

Simulation success is not physical-HIL validation.

### ZU2CG

```text
RTL simulation
    -> FPGA internal/connector loopback
    -> servo DUT digital interfaces
    -> DAC evaluation board
    -> closed-loop PMSM HIL
```

### BBB

```text
PRU build/test
    -> PRU/header loopback
    -> protected digital adapter
    -> servo DUT PWM/ABZ
    -> deterministic fault-response regression
```

## Required traceability

Every hardware result must record:

- backend name;
- board/revision;
- FPGA bitstream or PRU firmware revision;
- DUT hardware revision;
- DUT firmware commit;
- adapter/wiring revision;
- timing source/tick frequency;
- test configuration and pass/fail limits.

Infrastructure failure must be reported separately from DUT failure.
