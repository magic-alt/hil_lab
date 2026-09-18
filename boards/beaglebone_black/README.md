# BeagleBone Black / AM3358 PRU backend

Status: **B0 implementation in progress**. See #11-#15.

BeagleBone Black is the companion Digital-HIL backend. ZU2CG/AXU2CGB remains the primary Full-HIL path for DAC/analog feedback, PMSM plant execution, custom ADC/DAC hardware and robotic-joint models.

## B0 implemented software baseline

The `feat/b0-bbb-pru-bringup` work establishes:

- PRU0 firmware built with TI PRU CGT + PRU Software Support Package;
- remoteproc resource table and RPMsg port 30;
- fixed 32-byte capability/timebase command protocol;
- IEP 32-bit hardware timebase metadata;
- local safe-state/watchdog behavior;
- automatic remoteproc firmware install/start/stop script;
- Python RPMsg client for HELLO/TIME/PING/SAFE/LOOPBACK;
- temporary deterministic GPIO loopback using P9_31 -> P9_25;
- software-only protocol/static checks suitable for normal GitHub Actions.

Detailed target bring-up: [B0_BRINGUP.md](B0_BRINGUP.md).

## Real-time boundary

Time-critical work executes on PRU. Linux is the control plane only.

Linux may:

- load/start/stop firmware;
- configure tests;
- exchange parameters/results;
- log/report data.

Linux userspace must not bit-bang timing-critical PWM/ABZ/fault sequences as a substitute for PRU implementation.

## B0 temporary PRU0 allocation

```text
PRU0
├── IEP timebase
├── RPMsg control plane
├── P9_31 R30[0] loopback output
├── P9_25 R31[7] loopback input
└── watchdog / safe state
```

This is a qualification fixture, not the final servo-DUT pin map.

After B0 hardware evidence is complete:

```text
B1: PWM capture/dead-time
B2: ABZ generator
B3: deterministic fault/stimulus GPIO
B4: common backend/pytest conformance
```

The final PRU0/PRU1 responsibility split remains open until B0/B1 timing measurements are available.

## Safety

Raw BBB GPIO is 3.3 V logic. Do not connect it directly to:

- 24/48 V brake power;
- DC bus or motor phases;
- gate-driver power nodes;
- destructive short/open injection paths.

Final DUT wiring requires reviewed level translation, buffering/isolation and fault-insertion hardware.
