# AGENTS.md — AI Coding Contract

This file is the primary instruction set for AI coding tools working in `hil_lab`.

## 1. Project intent

Build a safe, reproducible servo-drive HIL platform. The current generation is signal-level only: PWM, low-voltage sensor emulation, encoder interfaces and communications. Do not add direct high-energy power-stage interaction without an explicit later design review.

## 2. RTL language boundary

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

Vendor-specific clocking, I/O buffers and constraints belong under `boards/<board>/`.

## 3. Design rules

Before changing RTL:

1. identify the clock/reset domain;
2. identify every asynchronous input and its CDC treatment;
3. define reset/safe-state behavior;
4. define measurement units and counter rollover behavior;
5. add or update a self-checking simulation;
6. update interface documentation when ports or semantics change.

Prefer small composable modules over board-specific monoliths.

## 4. Verification gate

Before proposing a change, run:

```bash
make verify
```

A change is incomplete if it changes synthesizable behavior without a regression test or an explicit reason why a test cannot yet be written.

Never "fix" a failing test by only weakening its assertion. Explain the expected hardware behavior first.

## 5. Generated files

Do not commit:

- Vivado `.runs/`, `.cache/`, `.gen/`, `.Xil/` output;
- bitstreams unless a release process explicitly requires them;
- simulator build products;
- local virtual environments;
- machine-specific IDE metadata.

Prefer reproducible Tcl scripts for future Vivado project generation.

## 6. Commit / PR conventions

Use focused conventional-style commit subjects where practical:

- `feat:` new HIL capability;
- `fix:` bug fix;
- `test:` verification only;
- `docs:` documentation only;
- `ci:` CI/build changes;
- `refactor:` behavior-preserving RTL change;
- `chore:` repository maintenance.

PR descriptions should include:

- intent and safety boundary;
- changed interfaces;
- verification performed;
- hardware validation still required;
- roadmap gate affected.

## 7. Current priorities

Until G0 is closed, prioritize in this order:

1. deterministic PWM measurement;
2. encoder emulation;
3. digital event scheduling;
4. exact ZU2CG board integration;
5. physical loopback and DUT validation.

Do not jump to PMSM or custom ADC/DAC PCB implementation before the digital timing path is proven unless a parallel design task is explicitly requested.
