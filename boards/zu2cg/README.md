# ALINX AXU2CGB target

The first physical HIL target is the **ALINX AXU2CGB** using
`XCZU2CG-1SFVC784E`.

## Verified vendor facts used by this target

- FPGA part: `xczu2cg-sfvc784-1-e`.
- PL reference clock: 25 MHz on package pin `AB11` (`IO_L8P_44`).
- J12 and J15 are 40-pin, 2.54 mm expansion headers with 34 FPGA I/Os each.
- Expansion-header logic is 3.3 V; never connect 5 V logic directly.
- On-board user LEDs are W13/Y12/AA12/AB13 and are used as active-low status outputs.

Primary vendor sources:

- <https://github.com/alinxalinx/AXU2CGA_AXU2CGB>
- <https://github.com/alinxalinx/AXU2CGA_AXU2CGB/blob/master/vivado/auto_create_project/src/constraints/system.xdc>
- <https://github.com/alinxalinx/AXU2CGA_AXU2CGB/blob/master/vivado/auto_create_project/project_info.tcl>

ALINX's hardware manual text says the PL reference clock level is +1.8 V,
while the vendor factory XDC and ALINX PLL tutorial constrain AB11 as
`LVCMOS33`. This target follows the factory XDC. Treat the discrepancy as a
hardware-qualification item: verify the exact board revision and clock waveform
before relying on the bench for quantitative timing measurements.

## Clocking

The physical board provides only 25 MHz. `axu2cgb_clock_gen.v` uses:

```text
AB11 / 25 MHz HDGC
        |
       BUFG
        |
      MMCM
        |
       BUFG
        |
100 MHz HIL clock (10 ns tick)
```

The input BUFG is intentional. ALINX's PLL tutorial notes that this HDGC input
must be buffered before an MMCM/PLL.

## Header allocation

G0 uses a direction-oriented split:

- **J12**: DUT -> HIL PWM/SPI plus bench-control inputs.
- **J15**: HIL -> DUT ABZ/SPI/DIO/status outputs.

This is a signal-level contract only. A DUT adapter must add protection and
level translation where the servo controller is not native 3.3 V logic.

### J12 input map

| J12 pin | FPGA pin | HIL signal |
|---:|---|---|
| 3 | F7 | PWM U high |
| 4 | G8 | PWM U low |
| 5 | F6 | PWM V high |
| 6 | G6 | PWM V low |
| 7 | D9 | PWM W high |
| 8 | E9 | PWM W low |
| 9 | F5 | SPI SCLK |
| 10 | G5 | SPI CS_n |
| 11 | E8 | SPI MOSI |
| 12 | F8 | external reset_n |
| 13 | D5 | HIL enable |
| 14 | E5 | encoder direction |
| 15 | C4 | clear PWM faults |
| 16 | D4 | FORCE_SAFE |
| 17 | E3 | digital test-pattern enable |

### J15 output map

| J15 pin | FPGA pin | HIL signal |
|---:|---|---|
| 3 | A11 | encoder A |
| 4 | A12 | encoder B |
| 5 | A13 | encoder Z |
| 6 | B13 | SPI MISO |
| 7..22 | A14..H14 | DIO[0..15] |
| 23 | G14 | clock locked |
| 24 | G15 | HIL reset released |
| 25 | F10 | PWM seen latch |
| 26 | G11 | PWM fault summary |

See `constraints/axu2cgb_hil.xdc` for the authoritative package-pin mapping.

## Fail-safe defaults

The XDC deliberately configures disconnected control inputs to a safe state:

- `HIL_ENABLE`: pull-down;
- `FORCE_SAFE`: pull-up;
- `SPI_CS_n`: pull-up;
- PWM inputs: pull-down;
- test-pattern enable: pull-down.

Physical ABZ/SPI/DIO outputs are suppressed unless `HIL_ENABLE=1` and
`FORCE_SAFE=0` after the 100 MHz clock is locked and reset is synchronously
released.

## Reproducible Vivado build

Create the project:

```bash
vivado -mode batch -source boards/zu2cg/scripts/create_project.tcl
```

Build a bitstream plus timing/utilization/DRC reports:

```bash
vivado -mode batch -source boards/zu2cg/scripts/build_bitstream.tcl
```

Generated Vivado files stay under `build/` and are not committed.

## G0 hardware qualification sequence

1. Build and program only the AXU2CGB, with no servo DUT connected.
2. Confirm LED1 indicates HIL clock lock/reset release.
3. Assert HIL enable, deassert FORCE_SAFE and assert test-pattern enable.
4. Measure J15 DIO and confirm `0xA55A` before attaching a DUT adapter.
5. Check ABZ amplitude/timing with a logic analyzer.
6. Connect a 3.3 V PWM source and confirm PWM-seen status.
7. Compare HIL dead-time/fault behavior with an oscilloscope reference.
8. Connect SPI to the servo MCU and verify the fixed G0 frame.
9. Only then connect the actual servo controller through a protected adapter.

G0 remains open until these physical checks are recorded in issue #1.
