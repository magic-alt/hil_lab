# BeagleBone Black / AM3358 PRU backend

Status: **planned companion Digital-HIL backend**. See #11-#15.

## Role

BeagleBone Black is used for deterministic controller-side digital testing:

- servo PWM capture and dead-time measurement;
- ABZ encoder generation;
- timestamped digital stimulus/fault GPIO;
- rapid hardware regression against GD32/HPM servo controllers.

It does not replace the ZU2CG/AXU2CGB Full-HIL backend.

## Real-time boundary

Time-critical work must execute on PRU.

Linux may:

- load/start/stop firmware;
- configure tests;
- exchange parameters/results;
- log/report data.

Linux userspace must not bit-bang timing-critical PWM/ABZ/fault sequences as a substitute for PRU implementation.

## Initial partition

The final PRU split is frozen only after B0 timing/resource measurements.

Reference direction:

```text
PRU0: capture-oriented
  - PWM edges
  - period/high/low
  - complementary dead-time
  - event counters

PRU1: generation/event-oriented
  - ABZ transitions
  - timestamped DIO/fault events
  - watchdog/safe-state handling
```

If measurements show a different partition is more deterministic, implementation may change while preserving the common backend contract.

## Timing

B0 must select and document the hardware timestamp source.

Host-visible metadata includes:

- tick frequency;
- counter width;
- rollover behavior;
- firmware/API version.

No test should assume a 5 ns timing quantum merely from the nominal PRU clock without physical characterization of the actual capture/generation path.

## Pinmux and adapter

Do not freeze a final P8/P9 DUT mapping until:

- required PRU direct-I/O pins are identified;
- onboard peripheral conflicts are checked;
- boot/default states are checked;
- the protected DUT adapter is reviewed.

Raw BBB GPIO is 3.3 V logic and is not a universal servo interface.

Use appropriate:

- level translation;
- buffering;
- RS-422 line drivers for differential encoders;
- isolation where grounding requires it;
- relays/analog switches for protected disconnect/fault paths.

Never connect raw BBB pins directly to 24/48 V brake or power-stage nodes.

## Bring-up sequence

1. B0 #11 — toolchain, remoteproc, transport, timebase, pinmux, safe state.
2. B1 #12 — 20 kHz PWM/dead-time capture.
3. B2 #13 — ABZ generator.
4. B3 #14 — deterministic fault/stimulus scheduler.
5. B4 #15 — common host API and pytest conformance.

## Suggested future subtree

```text
boards/beaglebone_black/
├── README.md
├── firmware/
│   ├── common/
│   ├── pru0_capture/
│   └── pru1_stimulus/
├── host/
├── pinmux/
└── tests/
    ├── loopback/
    └── hardware/
```

This layout is guidance for B0, not a requirement to commit empty directories.
