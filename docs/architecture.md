# Architecture — Multi-Backend Servo HIL v2

## Objective

hil_lab is a signal-level HIL and automated-test platform for servo drives and robotic actuators. Architecture v2 separates deterministic signal execution from Linux orchestration so each board is used for the job it is technically good at.

## Four roles

| Track | Platform | Role |
|---|---|---|
| A | ZU2CG / AXU2CGB | Full-HIL reference: FPGA timing, analog feedback, PMSM and later joint models |
| B | BeagleBone Black / AM3358 PRU | Digital-HIL / ServoBus analyzer: capture, timestamp, encoder/sensor stimulus, digital faults |
| C | Zynq-7010 / AX7010, later Zybo | FPGA-Lite: parallel signal HIL and resource-bounded single-motor plant |
| D | Raspberry Pi 4/5 | Linux HIL Controller: fieldbus, pytest/labgrid, DUT lifecycle, artifacts |

The first three are deterministic backends. Track D is a controller/service plane.

## Layering

~~~text
test intent / pytest / labgrid / optional ROS2
                    |
              host.hil contract
        capability + scenario + evidence
                    |
       +------------+-------------+
       |            |             |
     ZU2CG        AX7010         BBB PRU
       |            |             |
       +------- protected DUT -----+
                    |
                servo DUT

fieldbus/ is driven by the Linux controller and participates in the same
scenario/evidence model without moving edge timing into Linux userspace.
~~~

## Ownership rules

Linux owns configuration, DUT lifecycle, fieldbus commands, resource locking, reports and artifact collection.

FPGA PL or PRU owns edge capture, hardware timestamps, encoder/sensor transitions, local queued events, hard safe-state actions and plant stepping.

A backend must never advertise a deterministic capability that is implemented by ordinary Linux userspace sleeps or GPIO toggles.

## Time contract

Hardware time is represented by ticks, tick_hz and counter_bits. Raw ticks remain in evidence. Conversion to SI time is derived metadata.

Cross-device correlation may use NTP/PTP or measured trigger relationships, but host wall-clock time never replaces backend timestamps for timing assertions.

## Scenario model

A host scenario declares required capabilities and timestamp-ordered actions. The host validates support before execution. A deterministic backend may translate scenario actions into a local queue so Linux is not responsible for firing real-time edges.

The first versioned example is lab/scenarios/smoke_pwm_abz_fault.json.

## Source architecture

Architecture v2 target taxonomy:

~~~text
rtl/common/{timebase,fifo,snapshot,fault}
rtl/capture
rtl/generator
rtl/plant
rtl/scenario

pru/{capture,timestamp,protocol,shared_memory}
fieldbus/ethercat/{igh,soem,soes}
fieldbus/canopen
host/{hil,cli,ros2}
tests/{unit,cocotb,pytest,hil}
lab/{labgrid,resources,scenarios}
~~~

Phase 1-4 is complete through Scenario Engine v1: timebase, capture, generator/emulator and deterministic scenario RTL are canonical under `rtl/common/timebase/`, `rtl/capture/`, `rtl/generator/` and `rtl/scenario/`. Plant and DAC families remain in legacy paths until each coherent family moves with all build references. See migration-v2.md.

## Board boundaries

### ZU2CG

Full-HIL reference. Board-specific clocking, constraints and analog wiring remain under boards/zu2cg. G1+ adds DAC feedback, G2 PMSM closed loop, G3 custom analog I/O and G6 joint dynamics.

### AX7010 / Zybo

FPGA-Lite. Reuse generic Verilog cores; keep XDC/clock/board top separate. Zybo is a secondary XC7Z010 constraints target, not a fork of the logic.

### BeagleBone Black

PRU keeps deterministic I/O local. Current board-specific firmware remains under boards/beaglebone_black while top-level pru defines reusable architecture boundaries. Do not duplicate firmware merely to satisfy the directory layout.

### Raspberry Pi

Runs host/controller services, IgH/SOEM, SocketCAN/CANopen, pytest/labgrid and optional ROS2. PREEMPT_RT is a measurable configuration, not proof of EtherCAT performance by itself.

## Safety invariant

Every deterministic backend has a local force-safe/watchdog behavior independent of host responsiveness. Signal adapters own level translation, isolation, differential drivers, clamping and reviewed fault insertion.

High-energy DC-bus, motor-phase and brake-power fault injection remains out of Generation 1 scope.
