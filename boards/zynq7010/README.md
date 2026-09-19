# Zynq-7010 FPGA-Lite HIL target

The first Zynq-7010 target is the **ALINX AX7010** (XC7Z010-1CLG400).
The Digilent Zybo/Zybo Z7-10 remains a future pin-constraint target for the
same reusable FPGA-Lite cores.

## Why AX7010 first

For servo HIL the limiting board-level resource is usually deterministic PL I/O,
not the dual Cortex-A9 CPU. AX7010 provides:

- a dedicated 50 MHz PL clock on U18;
- two 40-pin, 2.54 mm PL expansion headers (J10, J11);
- 34 PL I/O on each expansion header;
- default 3.3 V PL I/O;
- 33 ohm series resistors between FPGA and expansion headers;
- differential-pair PCB routing on the expansion headers.

That gives enough direct PL pins to keep a clean direction-oriented split:
six PWM inputs, six PWM outputs, ABZ in/out, synchronous encoder links,
fault/status lines and future ADC/DAC control.

The Zybo family remains useful and the reusable RTL is not AX7010-specific.
For the Zybo Z7-10 specifically, fewer FPGA I/O are exposed and the standard
Pmod ports use 200 ohm series resistors, which Digilent notes can limit maximum
switching speed. A Zybo target can therefore be added later as a constraints
and electrical-interface variant without changing the core logic.

Primary board references:

- ALINX AX7010 2023.1 repository:
  https://github.com/alinxalinx/AX7010_2023.1
- ALINX AX7010 hardware manual:
  https://ax7010-20231-v101.readthedocs.io/zh-cn/latest/AX7010UserManual_CN/AX7010UserManual.html
- Digilent Zybo Z7 reference manual:
  https://digilent.com/reference/_media/reference/programmable-logic/zybo-z7/zybo-z7_rm.pdf

## FPGA-Lite role

This backend sits between the BBB PRU Digital-HIL backend and the ZU2CG
Full-HIL backend.

    BBB / PRU                 AX7010 / Zynq-7010             ZU2CG
    Digital HIL               FPGA-Lite HIL                  Full HIL
    -----------               -------------                  --------
    PWM capture               parallel PWM gen/capture      all FPGA-Lite work
    ABZ stimulus              ABZ gen/capture               high-rate ADC/DAC
    digital fault             SSI/SPI-style protocols       full PMSM plant
    timing profiler           deterministic fault I/O       dual-inertia joint
                              PMSM-lite single motor        multi-axis growth

Zynq-7010 is **not** intended to replace ZU2CG for the final multi-axis,
high-channel-count analog Full-HIL path.

## Implemented baseline

Reusable RTL added by this target:

- rtl/generator/pwm_complementary_generator.v
  - complementary high/low PWM generation;
  - configurable period, high time and dead time;
  - deterministic zero-output disabled state.
- existing pwm_capture + pwm_complementary_monitor
  - period/high/low timing;
  - dead-time measurement;
  - overlap and minimum-dead-time fault latching.
- rtl/encoder/abz_encoder_capture.v
  - x4 quadrature transition decode;
  - direction, edge position and index detection;
  - illegal transition latch.
- existing abz_encoder_emulator
  - deterministic ABZ generation.
- rtl/generator/ssi_encoder_emulator.v
  - MSB-first synchronous position-word emulation;
  - frame-gap recognition;
  - fault bit-flip hook.
- rtl/encoder/ssi_encoder_master_capture.v
  - deterministic SSI-style clock generation;
  - synchronous position-word acquisition.
- rtl/plant/averaged_inverter_abc_q16.v
  - averaged three-leg duty/Vbus reconstruction to line-neutral phase voltages;
  - common-mode removal in Q16.16.
- rtl/plant/pmsm_mechanics_q16.v
  - reusable torque/load/viscous-damping mechanical state integrator.
- rtl/plant/pmsm_dq_plant_q16.v
  - fixed-step Q16.16 averaged dq plant;
  - configurable discrete-time electrical/mechanical gains;
  - single-motor FPGA-Lite model before the ZU2CG Full-HIL plant.

The existing SPI mode-0 encoder emulator remains reusable on this backend.
BiSS-C framing/CRC is intentionally a later extension rather than being
misrepresented as plain SSI.

## Clocking

Physical AX7010:

    U18 / 50 MHz PL oscillator
            |
           BUFG
            |
       MMCME2_BASE
            |
           BUFG
            |
    100 MHz HIL clock = 10 ns/tick

HIL_SIMULATION bypasses the MMCM so dependency-free Icarus simulation does
not require Xilinx UNISIM libraries.

## Header allocation

### J10 — DUT -> HIL

| J10 | FPGA | Signal |
|---:|---|---|
| 3 | W19 | PWM U high input |
| 4 | W18 | PWM U low input |
| 5 | R14 | PWM V high input |
| 6 | P14 | PWM V low input |
| 7 | Y17 | PWM W high input |
| 8 | Y16 | PWM W low input |
| 9 | W15 | encoder A input |
| 10 | V15 | encoder B input |
| 11 | Y14 | encoder Z input |
| 12 | W14 | SSI data input |
| 13 | P18 | SSI clock from DUT |
| 15 | U15 | external reset_n |
| 16 | U14 | HIL enable |
| 17 | P16 | FORCE_SAFE |
| 18 | P15 | clear faults |
| 19 | U17 | encoder direction |
| 20 | T16 | SSI master start |

### J11 — HIL -> DUT

| J11 | FPGA | Signal |
|---:|---|---|
| 3 | F17 | PWM U high stimulus |
| 4 | F16 | PWM U low stimulus |
| 5 | F20 | PWM V high stimulus |
| 6 | F19 | PWM V low stimulus |
| 7 | G20 | PWM W high stimulus |
| 8 | G19 | PWM W low stimulus |
| 9 | H18 | encoder A stimulus |
| 10 | J18 | encoder B stimulus |
| 11 | L20 | encoder Z stimulus |
| 12 | L19 | SSI clock stimulus |
| 13 | M20 | SSI data stimulus |
| 14 | M19 | fault summary |
| 15..18 | K18/K17/J19/K19 | status[0..3] |

The board's four PL LEDs are used as active-low status indicators.

## Safety boundary

AX7010 expansion I/O is **3.3 V logic**. Never connect 5 V logic directly.

Raw FPGA pins also must not connect directly to:

- 24/48 V brake power;
- DC bus or motor phases;
- gate-driver power nodes;
- destructive short/open injection paths;
- RS-422 differential encoder wiring without a proper line receiver/driver.

Use a reviewed adapter for level shifting, isolation, differential drivers,
clamps, analog switches and protected fault routing.

FORCE_SAFE is pulled high in the XDC; HIL enable is pulled low. Stimulus
PWM/ABZ/fault outputs are suppressed when safe state is active.

## Vivado build

Create the project:

    vivado -mode batch -source boards/zynq7010/scripts/create_project.tcl

Build bitstream and reports:

    vivado -mode batch -source boards/zynq7010/scripts/build_bitstream.tcl

Generated files remain under build/zynq7010_ax7010/.

## Initial hardware qualification

1. Program AX7010 without a DUT attached.
2. Verify 100 MHz clock lock and LED status.
3. Confirm FORCE_SAFE suppresses all active stimulus outputs.
4. Measure the three generated complementary PWM pairs and dead time.
5. Loop generated PWM back into J10 and compare capture results with a scope.
6. Loop generated ABZ into J10 and verify direction/count/illegal-transition behavior.
7. Loop SSI master/emulator paths and verify the expected frame.
8. Only then attach the servo controller through the protected adapter.
