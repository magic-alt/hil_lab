# B2 PRU1 stimulus / emulation — ABZ baseline

Issue: #13

B2 turns PRU1 into the deterministic digital stimulus/emulation engine while PRU0 remains the capture engine.

## Architecture

Linux/RPMsg configures rate, direction, initial phase and index behavior. PRU1 owns every real-time ABZ edge.

First B2.1 map:

| Signal | BBB pin | PRU1 output |
| --- | --- | --- |
| A | P8_45 | R30[0] |
| B | P8_46 | R30[1] |
| Z | P8_43 | R30[2] |

Configure pins:

    cd ~/hil_lab/boards/beaglebone_black
    sudo sh pinmux/setup_b2_abz_outputs.sh

These P8 pins overlap the BBB LCD/HDMI pin group. Use a headless configuration and ensure the active device-tree/cape setup leaves them available for `pruout`.

## PRU1 RPMsg

- PRU -> ARM system event: 18
- ARM -> PRU system event: 19
- Host interrupt: Host1 / R31[31]
- RPMsg port: 31
- firmware name: `am335x-pru1-fw`

The PRU1 controller is discovered by name (`4a338000.pru` / `pruss-core1`) rather than assuming a fixed remoteproc number.

## Quadrature convention

Forward A/B sequence is `00 -> 10 -> 11 -> 01 -> 00`, so A leads B. Reverse traverses the same Gray-code states in the opposite direction.

The generator changes one state every `transition_ticks`.

For PPR-style host configuration:

    transition_rate = rpm / 60 * PPR * 4
    transition_ticks = 200 MHz / transition_rate

The host CLI performs this conversion.

## Index behavior

`index_period_transitions` and `index_width_transitions` are expressed in quadrature transitions. For one Z pulse per mechanical revolution, use `index_period_transitions = PPR * 4`. Set period to 0 to disable Z.

## Timing model

PRU1 uses the PRU-ICSS IEP 200 MHz counter. If PRU0 already started the IEP, PRU1 does not reset it.

Ordinary sub-period jitter keeps the phase-locked next deadline. If execution is late by at least one entire transition interval, `late_transition_count` increments and the next deadline is resynchronized from the actual current time rather than emitting compressed catch-up transitions.

The initial firmware guard is 100 IEP ticks = 500 ns per transition. This is not a qualified maximum rate; the real limit must be measured.

## Safe state

B2.1 safe state is A=B=Z=0. It is applied before Linux/RPMsg is ready, on ABZ_STOP, on FORCE_SAFE, and if RPMsg initialization fails.

Physical PRU-stop / host-loss qualification remains open for later B2/B3 acceptance.

## Build

    cd ~/hil_lab
    unset PSSP_DIR
    export PRU_CGT=/usr/share/ti/cgt-pru
    make bbb-b2-pru-env
    make bbb-b2-pru-build

Expected artifact:

    boards/beaglebone_black/firmware/pru1_b2/gen/hil_b2_pru1.out

## Deploy

    cd ~/hil_lab/boards/beaglebone_black
    sudo sh pinmux/setup_b2_abz_outputs.sh
    sudo python3 scripts/pru1_ctl.py deploy firmware/pru1_b2/gen/hil_b2_pru1.out

Expected RPMsg device: `/dev/rpmsg_pru31`.

Verify:

    cd host
    python3 hil_stim_cli.py hello

Expected firmware version: `0x00030000`.

## Example: 1000 PPR, 60 rpm

    python3 hil_stim_cli.py config --rpm 60 --ppr 1000 --direction forward --initial-phase 0
    python3 hil_stim_cli.py start
    python3 hil_stim_cli.py status

This resolves to 4000 transitions/s, 50000 IEP ticks/transition, and 250 us/transition.

Reverse while running:

    python3 hil_stim_cli.py direction reverse

Stop and force low:

    python3 hil_stim_cli.py stop
    python3 hil_stim_cli.py safe

## First physical verification

Logic analyzer wiring:

- CH0 -> P8_45 / A
- CH1 -> P8_46 / B
- CH2 -> P8_43 / Z
- GND -> BBB GND

Verify forward and reverse Gray-code order, requested transition period, Z period/width, no compressed burst after host commands, `late_transition_count == 0` at the tested rate, and STOP/FORCE_SAFE returning all outputs low.

## Remaining #13 work

This baseline does not close #13. Still open: timestamped schedule queue, deterministic speed step/reversal independent of RPMsg service time, ABZ fault variants, Hall/generic pulse mode, sustained max-rate characterization, real servo QEP validation, one serial sensor emulator, and physical host-loss/PRU-stop safe-state qualification.
