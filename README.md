# hil_lab

`hil_lab` is a signal-level hardware-in-the-loop (HIL) and automated-test platform for servo drives and robotic actuators.

The project now has **three cooperating real-time backends**:

- **Track A — ZU2CG / AXU2CGB Full HIL (primary):** FPGA digital timing, DAC/analog feedback, PMSM plant, custom ADC/DAC hardware and later robotic-joint models.
- **Track B — BeagleBone Black / AM3358 PRU Digital HIL (companion):** fast PWM measurement, ABZ generation, deterministic digital fault/stimulus I/O and rapid servo-firmware regression.
- **Track C — Zynq-7010 / AX7010 FPGA-Lite HIL:** low-cost parallel FPGA signal HIL, PWM generation/capture, encoder generation/capture and a resource-bounded single-motor plant.

BBB and Zynq-7010 do **not** replace the Zynq MPSoC roadmap. They provide lower-cost deterministic test targets while ZU2CG continues toward the full closed-loop multi-axis plant.

## Current development state

### ZU2CG / AXU2CGB

G0 reusable RTL and the physical AXU2CGB board integration are in place:

- FPGA timebase;
- PWM period/high/low capture;
- complementary PWM dead-time monitoring;
- overlap/minimum-dead-time fault latching;
- ABZ encoder emulation;
- SPI mode-0 sensor/encoder emulation;
- timestamped DIO event scheduling;
- exact AXU2CGB clock/pin integration and reproducible Vivado Tcl flow;
- Icarus/Verilator/GitHub Actions verification.

Physical G0 validation against the actual AXU2CGB and servo DUT remains open in #1.

G1 analog feedback is tracked in #3 / PR #10 using two AD3542R evaluation DACs. RTL and CI work are implemented; level-shifter/interposer and physical analog characterization remain required.

### Zynq-7010 / AX7010 FPGA-Lite

The AX7010 target is the first Track C board because its two 40-pin PL expansion
headers expose enough direct 3.3 V I/O for simultaneous six-PWM, ABZ, SSI,
fault/status and future ADC/DAC control. The current baseline adds:

- complementary PWM generation plus existing PWM/dead-time capture;
- ABZ generation and x4 quadrature capture;
- SSI-style encoder emulation and master capture;
- reusable SPI encoder emulation from the common RTL;
- a fixed-step Q16.16 PMSM-lite dq model for single-motor experiments;
- exact AX7010 J10/J11 constraints and a reproducible Vivado flow.

See `boards/zynq7010/README.md`.

### BeagleBone Black / PRU

The new companion track is split into:

- **B0 #11** — PRU platform, host transport, timestamp and safe-state bring-up;
- **B1 #12** — PRU PWM capture + complementary dead-time monitor;
- **B2 #13** — PRU ABZ encoder generator;
- **B3 #14** — deterministic fault/stimulus GPIO scheduler;
- **B4 #15** — common HIL backend API + cross-target pytest conformance.

## Architecture

```text
                    host / pytest / Servo CI
                             |
                    common HIL contract
                 capability + time + events
                    /                   \
                   /                     \
        ZU2CG / AXU2CGB               BBB / AM3358
        Full-HIL backend              PRU digital backend
        ----------------              -------------------
        FPGA timebase                 PRU timestamp
        PWM capture                   PWM capture
        ABZ/SPI emulation             ABZ generation
        deterministic DIO             fault/stimulus GPIO
        DAC / analog feedback         digital only
        PMSM plant (future)           no PMSM requirement
                |                           |
                +------------+--------------+
                             |
                     protected DUT adapter
                             |
                      GD32/HPM servo DUT
```

Cross-platform reuse is at the **semantic contract and test layer**. FPGA RTL and PRU firmware remain platform-specific where that produces the most deterministic implementation.

## Safety boundary

Generation 1 remains a **Signal-Level Controller HIL**.

Do not connect FPGA or BBB headers directly to:

- the 48 V DC bus;
- motor phases;
- MOSFET drain/source nodes;
- 24/48 V brake power;
- destructive short/open fault paths.

Voltage translation, differential drivers, isolation, clamping, current limiting, analog switches and relays belong in reviewed adapters.

A host crash or communication loss must never leave a hazardous stimulus asserted. Real-time backends own their local safe-state behavior.

## Repository layout

```text
hil_lab/
├── rtl/                         reusable Zynq/FPGA Verilog-2001 RTL
├── sim/                         self-checking FPGA simulations
├── boards/
│   ├── zu2cg/                   AXU2CGB board integration
│   ├── zynq7010/                AX7010 FPGA-Lite HIL backend
│   ├── beaglebone_black/        PRU digital-HIL backend
│   └── stm32f429i_disc1/        Keil MDK multi-target 20 kHz PWM stimulus
├── docs/
│   ├── architecture.md
│   ├── backend-contract.md      shared behavioral contract
│   ├── io-contract.md
│   └── testing.md
├── tools/
├── .github/
├── AGENTS.md
├── Makefile
└── ROADMAP.md
```

## Verification

Current software/RTL gates:

```bash
sudo apt-get install iverilog verilator make python3
make verify
```

`make verify` also checks the AX7010 FPGA-Lite RTL/constraints/tests, BBB host/core contracts and the STM32F429I-DISC1 PWM stimulus configuration. Real Vivado bitstream builds, PRU builds and STM32 cross-compilation remain explicit hardware/toolchain steps.

Hardware evidence must always record:

- HIL backend and board revision;
- FPGA bitstream or PRU firmware revision;
- DUT hardware revision;
- DUT firmware commit;
- adapter/wiring revision;
- timestamp clock/tick definition.

## Development direction

### Track A — Full HIL

1. G0 ZU2CG Digital HIL physical qualification
2. G1 AD3542R 4-channel analog evaluation
3. G2 PMSM closed-loop HIL
4. G3 custom 8-channel ADC/DAC HIL PCB
5. G4 complete signal-level Fault Injection Unit
6. G5 unattended pytest/CI Servo HIL
7. G6 dual-inertia robotic-joint model

### Track B — fast digital HIL

1. B0 BBB PRU bring-up
2. B1 PWM/dead-time capture
3. B2 ABZ generator
4. B3 deterministic digital fault/stimulus scheduler
5. B4 common backend API and conformance tests

The two tracks converge in G5/B4. New tests should target the common HIL semantics when possible and declare required capabilities explicitly.


### Track C — FPGA-Lite HIL

The Zynq-7010 lane provides a resource-bounded FPGA target between BBB PRU and
ZU2CG Full-HIL:

1. AX7010 board/clock/constraint bring-up;
2. parallel PWM generation and capture;
3. ABZ + SSI/SPI encoder generation/capture;
4. deterministic signal fault injection;
5. fixed-step single-motor PMSM-lite plant;
6. PS/AXI control and shared pytest backend integration.

The first target is AX7010. Zybo(7010) support should reuse the same cores and
add only board-specific clock/pin/electrical integration where possible.
