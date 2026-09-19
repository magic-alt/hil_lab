# Verification Strategy

Verification is layered so simulation, backend conformance and physical HIL evidence are not conflated.

## make verify

Architecture v2 adds two gates before the existing RTL/board checks:

1. architecture — validates architecture/manifest.json, required directories and capability registry consistency;
2. host-test — pytest tests for the backend/scenario contract;
3. existing Verilog policy/compile/simulation/lint;
4. DAC/AXU2CGB gates;
5. AX7010 gates;
6. BBB static/host/core gates;
7. MCU PWM stimulus checks.

CI installs pytest and runs the same make verify entry point.

## Test taxonomy

- tests/unit — dependency-light pure unit tests;
- tests/cocotb — future event/protocol/plant co-simulation;
- tests/pytest — backend-neutral host API and scenario conformance;
- tests/hil — hardware-required suites and resource definitions;
- sim — existing self-checking Icarus/Verilog benches retained during migration.

## Backend qualification ladders

ZU2CG:

~~~text
RTL simulation -> board loopback -> DUT digital -> DAC -> PMSM closed loop
~~~

AX7010/Zybo:

~~~text
RTL simulation -> timing/DRC -> connector loopback -> DUT signal HIL -> PMSM-lite
~~~

BBB:

~~~text
PRU static/build -> header loopback -> logic analyzer -> protected adapter -> DUT
~~~

Raspberry Pi controller:

~~~text
OS/service baseline -> cyclictest -> NIC/CAN -> fieldbus cycle evidence
-> common backend discovery -> labgrid/pytest unattended bench
~~~

PREEMPT_RT installation alone is not an EtherCAT pass criterion. Record cycle time, jitter, WKC and DC/SYNC evidence under representative load.

## Cross-backend conformance

Tests declare capabilities. The same semantic test may use backend-specific numerical tolerances but may not branch on board model when a capability check is sufficient.

Early overlap:

| Capability | ZU2CG | AX7010 | BBB |
|---|---:|---:|---:|
| timebase/force_safe | yes | yes | yes |
| PWM capture/dead-time | yes | yes | B1 |
| ABZ generation | yes | yes | B2 |
| deterministic DIO | yes | C3 | B3 |
| sensor emulation | SPI | SSI/SPI | B2 serial |
| analog feedback | G1 | external/future | no |
| PMSM plant | G2 | C4 lite | no |

## Scenario evidence

Every hardware run records:

- controller image/kernel revision where present;
- backend board/revision;
- bitstream or PRU firmware revision;
- DUT HW and firmware commit;
- adapter/wiring revision;
- tick frequency/counter width;
- fieldbus interface and configuration where used;
- scenario file/version;
- pass/fail limits;
- infrastructure errors separately from DUT assertions.

A failed or interrupted test must return the bench to a defined safe state before resource release.
