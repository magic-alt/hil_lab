# Servo HIL Roadmap

`hil_lab` uses two parallel development tracks with different responsibilities.

- **Track A (G-series): ZU2CG / AXU2CGB Full HIL** is the primary product path.
- **Track B (B-series): BeagleBone Black / PRU Digital HIL** is a companion path for rapid deterministic digital testing.

Track B accelerates firmware validation but does not replace Track A analog/PMSM/joint-model work.

# Track A — ZU2CG / AXU2CGB Full HIL

## G0 — ZU2CG FPGA Digital HIL

**Goal:** establish the safe deterministic FPGA baseline and validate it on the physical AXU2CGB plus a servo DUT.

Implemented:

- [x] synthesizable Verilog-2001 reusable RTL skeleton;
- [x] FPGA timestamp/timebase;
- [x] PWM period/high/low capture;
- [x] complementary dead-time monitor and fault latches;
- [x] ABZ encoder emulator;
- [x] SPI mode-0 sensor/encoder emulator;
- [x] deterministic DIO event scheduler;
- [x] self-checking simulations and CI;
- [x] exact AXU2CGB device/clock/pin integration;
- [x] reproducible Vivado project/bitstream Tcl;
- [x] board-top simulation and constraint-integrity checks.

Remaining exit criteria (#1):

- [ ] run physical Vivado implementation/timing/DRC evidence on the intended toolchain;
- [ ] program the AXU2CGB and validate connector loopback;
- [ ] resolve the physical PL reference-clock voltage-level documentation discrepancy;
- [ ] validate servo DUT 20 kHz PWM/dead-time measurement against an oscilloscope;
- [ ] validate ABZ and SPI emulation against a real servo MCU;
- [ ] validate at least one DUT communication path;
- [ ] freeze/review the first protected DUT adapter.

## G1 — 4-channel AD3542R analog-feedback evaluation

**Goal:** prove low-voltage current/bus sensor injection before a custom HIL PCB is designed.

Tracked by #3 / PR #10.

Implemented in the current G1 code path:

- [x] two-board AD3542R four-channel streaming architecture;
- [x] deterministic FPGA-to-DAC stream;
- [x] calibration pattern generation;
- [x] AXU2CGB integration;
- [x] external analog-output-enable safety seam;
- [x] compile/simulation/lint gates.

Remaining physical exit criteria:

- [ ] build/use the required 3.3 V <-> 1.8 V interposer;
- [ ] verify 50 MHz SPI through the interposer;
- [ ] demonstrate >=4 analog outputs;
- [ ] characterize gain/offset, settling, latency and inter-channel skew;
- [ ] verify independent analog clamp/safe-state behavior;
- [ ] inject Ia/Ib/Ic/Vbus into a real servo MCU ADC path.

## G2 — PMSM closed-loop HIL

**Goal:** close a real 20 kHz servo FOC loop without a physical motor.

Scope (#4):

- averaged inverter model;
- PMSM dq electrical model;
- mechanical inertia/friction model;
- PWM -> plant -> DAC feedback loop;
- simulated rotor state driving encoder feedback;
- explicit fixed-step and end-to-end latency budget.

Exit criteria:

- [ ] stable 20 kHz FOC current-loop closure;
- [ ] repeatable current steps and speed ramps;
- [ ] runtime-configurable motor parameters;
- [ ] numerical range/saturation regressions;
- [ ] measured model/PWM/DAC end-to-end latency.

## G3 — 8-channel ADC/DAC HIL PCB

**Goal:** replace evaluation boards with calibrated protected HIL analog I/O.

Tracked by #5. G1/G2 measurements define the PCB requirements; the PCB must not be designed around unverified timing assumptions.

## G4 — complete Fault Injection Unit

**Goal:** provide deterministic protected digital and analog signal-side fault injection.

Tracked by #6.

BBB B3 may deliver an early **digital subset**, but G4 remains responsible for the final ZU2CG/adapter-integrated FIU, including analog sensor faults and the production HIL electrical safety design.

## G5 — unattended pytest / Servo CI

**Goal:** turn the bench into a reproducible automated regression service.

Tracked by #7.

G5 consumes the common backend contract introduced by B4 so that digital tests can run on BBB or ZU2CG where capabilities overlap.

## G6 — dual-inertia robotic-joint model

**Goal:** evolve the PMSM plant into humanoid/robotic joint HIL.

Tracked by #8.

Scope remains motor/load inertia, gearbox ratio/efficiency, compliance/damping, friction, backlash where needed, dual encoders and output torque sensing.

# Track B — BeagleBone Black / PRU Digital HIL

## B0 — PRU backend bring-up (#11)

**Goal:** establish a safe, reproducible AM3358 PRU execution and host-control baseline.

Exit criteria:

- [ ] reproducible PRU build/load/start/stop;
- [ ] host <-> PRU capability/version/timestamp exchange;
- [ ] documented timer/tick and rollover semantics;
- [ ] documented pinmux/adapter ownership;
- [ ] demonstrated reset/host-loss safe state;
- [ ] deterministic GPIO loopback measurement.

## B1 — PRU PWM capture + dead-time (#12)

**Goal:** provide an independent deterministic implementation of the digital PWM measurement path.

Exit criteria:

- [ ] continuous 20 kHz servo PWM capture;
- [ ] period/high/low/dead-time measurements;
- [ ] overlap/minimum-dead-time detection;
- [ ] scope/logic-analyzer comparison;
- [ ] sustainable event-rate and timing error characterized.

## B2 — PRU ABZ encoder generator (#13)

**Goal:** drive a real servo MCU QEP/timer input without a motor encoder.

Exit criteria:

- [ ] valid forward/reverse quadrature;
- [ ] deterministic speed/direction updates;
- [ ] configurable index behavior;
- [ ] maximum transition rate characterized;
- [ ] real servo-MCU position/direction validation.

## B3 — deterministic fault/stimulus GPIO (#14)

**Goal:** make BBB useful as a servo firmware fault-injection box.

Exit criteria:

- [ ] timestamped arm/fire/clear events;
- [ ] masked multi-channel update;
- [ ] host-loss watchdog and safe recovery;
- [ ] at least one protected DUT fault path exercised;
- [ ] DUT reaction latency retained in test evidence.

## B4 — common backend API + pytest conformance (#15)

**Goal:** make BBB and ZU2CG two backends of one HIL system rather than two separate projects.

Required common semantics:

- backend identity/version/capabilities;
- monotonic timestamp metadata;
- PWM measurements;
- ABZ configuration/control;
- deterministic DIO scheduling;
- force-safe/reset;
- health/error counters.

ZU2CG-only analog/PMSM capabilities remain explicit capabilities and must not be approximated with nondeterministic Linux code on BBB.

# Convergence rules

1. **ZU2CG remains the reference Full-HIL implementation.**
2. **BBB is digital-only unless a later design explicitly expands it.**
3. Host tests specify capabilities, not board names.
4. Raw hardware time is represented as ticks plus clock metadata; conversion does not hide quantization.
5. Linux is the control plane. Time-critical capture/generation/scheduling stays in FPGA PL or PRU.
6. Unsupported capabilities fail/skip explicitly; they are never silently emulated with ordinary Linux GPIO timing.
7. G1/G2/G3 continue even while B0-B3 are being developed.
8. B4/G5 is the architectural convergence point.

# Immediate priority

Parallel work is now permitted:

**ZU2CG lane**

```text
G0 physical qualification
        +
G1 AD3542R physical qualification
        -> G2 PMSM closed loop
```

**BBB lane**

```text
B0 PRU bring-up
   -> B1 PWM capture
   -> B2 ABZ generator
   -> B3 Fault GPIO
   -> B4 common pytest backend
```

Neither lane is a prerequisite for abandoning or pausing the other.
