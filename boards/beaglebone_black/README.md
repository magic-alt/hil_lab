# BeagleBone Black / AM3358 PRU backend

Status: **B0/B1 runtime-qualified; B2 stimulus/emulation development active**. See #11-#15.

BeagleBone Black is the companion Digital-HIL backend. ZU2CG/AXU2CGB remains the primary Full-HIL path for DAC/analog feedback, PMSM plant execution, custom ADC/DAC hardware and robotic-joint models.

## B0 validated baseline

The real BBB has demonstrated:

- reproducible PRU0 build with TI PRU CGT + PSSP v6.0;
- remoteproc load/start/stop;
- RPMsg port 30 and `/dev/rpmsg_pru30`;
- HELLO/TIME/PING protocol exchange;
- IEP 200 MHz / 32-bit timebase metadata;
- deterministic P9_31 -> P9_29 loopback;
- persistent 1000-sample benchmark with 0 failures;
- PRU-side rise observation latency 0.245 us and 1000.085 us measured high width for the 1 ms loopback fixture.

Detailed target bring-up: [B0_BRINGUP.md](B0_BRINGUP.md).

## B1 PWM capture architecture

B1 turns PRU0 into the capture/data-plane engine.

```text
six direct R31 inputs
        |
        v
single R31 sample
        |
edge bitmap
        |
IEP timestamp only on change
        |
period / high / low
dead-time H->L / L->H
overlap + min-DT latches
        |
PRUSS shared RAM snapshot + edge ring
        |
Linux /dev/mem batch/snapshot reader
```

RPMsg remains the control plane only:

- configure minimum dead-time;
- start/stop capture;
- clear counters;
- query capture status.

Individual PWM edges are never sent as one RPMsg each.

Detailed B1 notes: [B1_PWM_CAPTURE.md](B1_PWM_CAPTURE.md).

## B2 PRU1 stimulus / encoder emulation

B2 keeps deterministic stimulus generation on PRU1. The current implementation
covers ABZ with timestamped scheduling, Hall six-step generation and an
alternate SSI/BiSS-C/SPI-style serial-emulator firmware.

Detailed B2 notes: [B2_STIMULUS.md](B2_STIMULUS.md).


## B1 fixed first-board pin map

```text
UH -> P9_29 -> PRU0 R31[1]
UL -> P9_30 -> PRU0 R31[2]
VH -> P9_28 -> PRU0 R31[3]
VL -> P9_27 -> PRU0 R31[5]
WH -> P8_16 -> PRU0 R31[14]
WL -> P8_15 -> PRU0 R31[15]
```

This map deliberately avoids P9_25 and the more awkward P9_41/P9_42 mux cases.

## Safety

Raw BBB GPIO is 3.3 V logic. Do not connect it directly to:

- 24/48 V brake power;
- DC bus or motor phases;
- gate-driver power nodes;
- destructive short/open injection paths.

Final DUT wiring requires reviewed level translation, buffering/isolation and fault-insertion hardware.
