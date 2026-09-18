# AGENTS.md — AI Coding Contract

This file is the primary instruction set for AI coding tools working in `hil_lab`.

## 1. Project intent

Build a safe, reproducible servo-drive HIL platform with two cooperating real-time backends:

- **ZU2CG / AXU2CGB** is the primary Full-HIL path and owns FPGA timing, analog/DAC integration, PMSM closed-loop work and later robotic-joint models.
- **BeagleBone Black / AM3358 PRU** is a companion Digital-HIL path for PWM capture, ABZ generation and deterministic digital fault/stimulus testing.

Do not replace the ZU2CG roadmap with BBB work. Do not duplicate host-level test semantics independently in each backend.

The current generation remains signal-level only. Direct high-energy power-stage interaction requires an explicit later design review.

## 2. FPGA RTL language boundary

All synthesizable FPGA core RTL under `rtl/` MUST:

- use Verilog-2001 syntax and `.v` files;
- remain synthesizable;
- avoid SystemVerilog-only constructs;
- avoid HLS-generated RTL;
- avoid vendor primitives in reusable modules;
- use active-low reset `rst_n` unless a board wrapper documents otherwise;
- use non-blocking assignments in clocked processes;
- avoid gated clocks and inferred latches;
- synchronize asynchronous external inputs explicitly;
- expose timing values in clock ticks unless otherwise documented.

Vendor-specific FPGA clocking, I/O buffers and constraints belong under `boards/zu2cg/`.

## 3. BBB / PRU boundary

PRU firmware and BBB integration belong under `boards/beaglebone_black/` (or a later documented platform-specific source subtree).

PRU changes MUST:

- keep time-critical capture/generation/scheduling inside PRU, not Linux userspace;
- define the PRU clock/timestamp source and rollover semantics;
- define boot/reset/PRU-stop/host-loss output states;
- avoid busy Linux-side timing loops as a substitute for PRU determinism;
- avoid freezing a final physical pinout before the pinmux and protected DUT adapter are reviewed;
- expose capabilities and revision metadata to the host;
- include a loopback or hardware-verification procedure for timing behavior.

PRU C/assembly does not inherit the Verilog-2001 language rule.

## 4. Cross-backend design rule

Reuse behavior, not implementation.

Common semantics belong in the backend contract / host API:

- timestamp metadata;
- PWM measurement meaning;
- ABZ control meaning;
- deterministic DIO event meaning;
- safe/reset behavior;
- health/error reporting.

A backend may report a feature as unsupported. It must not silently degrade a deterministic feature into ordinary Linux scheduling just to satisfy an API.

## 5. Design checklist

Before changing real-time behavior:

1. identify the clock/timestamp domain;
2. identify asynchronous inputs and their treatment;
3. define reset and safe-state behavior;
4. define units, quantization and rollover/saturation behavior;
5. identify host/backend ownership;
6. add or update a self-checking simulation, unit test or hardware loopback test;
7. update interface documentation when semantics change.

Prefer small composable modules over board-specific monoliths.

## 6. Verification gates

FPGA changes must continue to pass:

```bash
make verify
```

BBB work must add independent PRU build/test gates; it may not weaken or bypass the FPGA gates.

Behavior that exists on both backends should gain a common conformance test as B4 matures.

Never "fix" a failing test by only weakening its assertion. Explain the expected hardware behavior first.

## 7. Generated files

Do not commit:

- Vivado `.runs/`, `.cache/`, `.gen/`, `.Xil/` output;
- bitstreams unless a release process explicitly requires them;
- simulator build products;
- PRU compiler temporary/build output;
- local virtual environments;
- machine-specific IDE metadata.

Prefer reproducible scripts for Vivado and PRU firmware builds.

## 8. Commit / PR conventions

Use focused conventional-style commit subjects where practical:

- `feat:` new HIL capability;
- `fix:` bug fix;
- `test:` verification only;
- `docs:` documentation only;
- `ci:` CI/build changes;
- `refactor:` behavior-preserving change;
- `chore:` repository maintenance.

PR descriptions should include:

- target backend(s);
- intent and safety boundary;
- changed interfaces/semantics;
- verification performed;
- hardware validation still required;
- roadmap gate/issue affected.

## 9. Current priorities

Parallel work is explicitly allowed.

### ZU2CG

1. finish G0 physical AXU2CGB + servo-DUT qualification;
2. finish G1 AD3542R physical characterization;
3. preserve the path to G2 PMSM closed-loop HIL.

### BBB

1. B0 PRU bring-up (#11);
2. B1 PWM/dead-time capture (#12);
3. B2 ABZ generator (#13);
4. B3 deterministic fault/stimulus GPIO (#14);
5. B4 backend conformance (#15).

Do not start a custom ADC/DAC PCB before G1/G2 measurements define its requirements.
