# Servo HIL Roadmap

This roadmap defines the product gates for `hil_lab`. Each gate must have measurable exit criteria before the next gate becomes the default development focus.

## G0 — ZU2CG FPGA Digital HIL

**Goal:** establish a safe, deterministic, vendor-light Signal-Level Controller HIL core.

Scope:

- PWM edge capture, period, high/low time and duty measurement;
- complementary PWM dead-time measurement;
- shoot-through-command detection;
- global FPGA timestamp;
- ABZ quadrature encoder emulation;
- SPI mode-0 absolute-encoder/sensor emulation;
- digital I/O event scheduler;
- ZU2CG board-integration seam;
- RTL simulation/lint CI;
- coding, review and AI-agent rules.

Exit criteria:

- [x] synthesizable Verilog-2001 reusable RTL skeleton;
- [x] self-checking simulations for the first digital blocks;
- [x] CI gate for RTL policy/compile/simulation/lint;
- [ ] ZU2CG reference clock/reset/pin constraints committed for the exact carrier board;
- [ ] loopback validated on physical FPGA hardware;
- [ ] servo DUT PWM capture validated at the intended 20 kHz switching frequency;
- [ ] ABZ and SPI encoder emulation validated against a real servo MCU.

## G1 — 4/8-channel DAC integration

**Goal:** inject low-voltage sensor feedback into the DUT ADC path.

Scope:

- evaluate a 4- or 8-channel DAC board before designing custom PCB hardware;
- deterministic FPGA-to-DAC update interface;
- 0–3.3 V DUT-facing current/voltage sensor emulation;
- offset/gain calibration table;
- output clamp and safe-state behavior.

Exit criteria:

- [ ] >= 4 synchronized analog outputs demonstrated;
- [ ] >= 1 MSPS target update path characterized;
- [ ] closed digital-to-analog loop latency measured;
- [ ] power-on and communication-loss outputs fail safe.

## G2 — PMSM closed-loop HIL

**Goal:** close the real servo FOC loop without a physical motor.

Scope:

- averaged three-phase inverter model;
- PMSM dq electrical model;
- simple inertia/friction mechanical model;
- PWM -> plant -> Ia/Ib/Ic -> DUT ADC feedback loop;
- encoder position generated from simulated rotor state.

Exit criteria:

- [ ] 20 kHz FOC current loop closes stably against the simulated plant;
- [ ] current steps and speed ramps are repeatable;
- [ ] model parameters are runtime configurable;
- [ ] numerical step/latency budget is documented.

## G3 — 8-channel ADC/DAC HIL PCB

**Goal:** replace evaluation boards with a calibrated HIL analog front end.

Target direction:

- 8x DAC, nominal 16-bit, >= 1 MSPS class;
- 8x ADC, nominal 16-bit, synchronized where practical;
- buffered and protected DUT-facing 0–3.3 V paths;
- internal bipolar range only where justified;
- digital isolation where it improves safety/grounding;
- EEPROM or software calibration data.

Exit criteria:

- [ ] schematic review and interface FMEA complete;
- [ ] prototype passes channel-to-channel gain/offset characterization;
- [ ] settling and end-to-end delay meet the HIL model budget;
- [ ] adapter-board interface is frozen.

## G4 — Fault Injection Unit

**Goal:** automate safe signal-side robustness tests.

Initial fault classes:

- encoder open/stuck/jump;
- SPI frame corruption and timeout;
- sensor offset and over/under-range;
- signal open/short-to-low/short-to-low-voltage-rail through protected circuitry;
- CAN/RS485/EtherCAT communication interruption at the appropriate interface layer;
- digital enable/fault/watchdog sequencing.

Power-stage destructive fault emulation is explicitly out of scope for this gate.

Exit criteria:

- [ ] each supported fault has deterministic trigger and timestamp;
- [ ] safe limits are enforced in hardware and software;
- [ ] test result records include injection time and DUT reaction latency.

## G5 — Automated pytest / CI regression

**Goal:** turn HIL into Servo CI rather than a manually operated bench.

Scope:

- host API;
- pytest fixtures and test-case metadata;
- firmware flashing / power-cycle orchestration;
- JUnit + waveform + measurement artifacts;
- hardware resource locking;
- self-hosted runner/HIL reservation model;
- pass/fail limits versioned with hardware and firmware.

Exit criteria:

- [ ] a firmware revision can execute a reproducible unattended HIL suite;
- [ ] failed tests retain enough waveform/context for diagnosis;
- [ ] CI distinguishes infrastructure failure from DUT failure.

## G6 — Dual-inertia robotic-joint model

**Goal:** evolve from generic motor HIL into humanoid-joint servo HIL.

Scope:

- motor inertia;
- gearbox ratio/efficiency;
- compliance and damping;
- load inertia;
- Coulomb/viscous friction;
- backlash/dead-zone where required;
- motor-side + output-side encoder model;
- output torque sensor model;
- harmonic, planetary and linear actuator parameter sets.

Exit criteria:

- [ ] resonance/anti-resonance behavior is reproducible;
- [ ] notch/DOB/ESO/controller changes can be compared automatically;
- [ ] dual-encoder and torque-loop regressions are supported.
