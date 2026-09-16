# Contributing

## Development flow

1. branch from the latest `main`;
2. keep one logical change per pull request;
3. update documentation for interface changes;
4. run `make verify`;
5. record hardware-only validation separately from simulation results.

## Definition of done

An RTL change is done when:

- the behavior and units are documented;
- reset and safe state are defined;
- asynchronous inputs have an explicit CDC strategy;
- at least one self-checking simulation covers the new behavior or bug;
- `make verify` passes;
- unresolved hardware validation is clearly listed in the PR.

## Hardware safety

The G0/G1 platform is intended for signal-level testing. Do not connect unprotected FPGA or analog-I/O pins directly to:

- DC bus rails;
- motor phases;
- MOSFET drain/source nodes;
- gate-driver switching nodes outside their logic-level interface;
- brake power outputs;
- other high-energy nets.
