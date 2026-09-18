# B0 BeagleBone Black PRU bring-up

Issue: #11

This gate establishes the minimal deterministic BBB backend before PWM capture, ABZ generation and fault scheduling are added.

## Baseline

- Board: BeagleBone Black / AM3358
- Real-time core: PRU0
- Firmware loading: Linux remoteproc (`am335x-pru0-fw` default)
- Host transport: RPMsg character device, port 30
- Hardware timebase: PRU IEP, configured for increment 1 at the nominal 200 MHz PRU/IEP clock
- Counter exposed by B0: 32 bits; host software must handle wrap explicitly
- Temporary loopback fixture: P9_31 PRU0 output -> P9_29 PRU0 input

The 200 MHz value is the configured/nominal timebase. Physical B0 qualification must measure GPIO command/observation latency and quantization; do not treat 5 ns as guaranteed end-to-end edge accuracy.

## Prerequisites on BBB

The image must expose PRU remoteproc/RPMsg. Verify:

```bash
ls /sys/class/remoteproc
cat /sys/class/remoteproc/remoteproc*/name
```

PRU0 is normally reported as `4a334000.pru` (or a closely related `4a334000.pru0` / `pruss-core0` name). The management script discovers it by name instead of assuming `remoteproc1`.

Install/provide:

- TI PRU Code Generation Tools (`PRU_CGT`)
- TI PRU Software Support Package (`PSSP_DIR`), including `include/` and `lib/rpmsg_lib.lib`
- `config-pin` for the temporary loopback fixture
- Python 3

Example environment on an ARM Debian image:

```bash
export PRU_CGT=/usr/share/ti/cgt-pru

# Usually auto-detected when installed here:
# /usr/lib/ti/pru-software-support-package
# You only need to export PSSP_DIR for a custom location.
```

Inspect what the build detected:

```bash
make bbb-pru-env
```

If PSSP is missing, install/clone the TI package:

```bash
sudo apt update
sudo apt install -y git ti-pru-cgt-v2.3
sudo mkdir -p /usr/lib/ti
sudo git clone --depth 1 --branch v6.5.0 \
  https://git.ti.com/git/pru-software-support-package/pru-software-support-package.git \
  /usr/lib/ti/pru-software-support-package
```

The required files are:

```text
/usr/lib/ti/pru-software-support-package/include/pru_rpmsg.h
/usr/lib/ti/pru-software-support-package/include/am335x/...
/usr/lib/ti/pru-software-support-package/lib/rpmsg_lib.lib
```

## Build

From repository root:

```bash
make bbb-check
make bbb-pru-build
```

or:

```bash
make -C boards/beaglebone_black check
make -C boards/beaglebone_black pru0
```

Firmware output:

```text
boards/beaglebone_black/firmware/pru0_b0/gen/hil_b0_pru0.out
```

## Configure temporary loopback pins

Stop PRU0 before changing the fixture if there is any doubt about the current firmware/output state.

```bash
cd boards/beaglebone_black
sudo ./pinmux/setup_b0_loopback.sh
```

Connect only:

```text
P9_31 -> P9_29
```

This mapping exists only for B0 timing validation. It is not the frozen GD32/HPM DUT adapter mapping.

## Deploy/restart without manual firmware copying

```bash
cd boards/beaglebone_black
sudo python3 scripts/pru0_ctl.py deploy firmware/pru0_b0/gen/hil_b0_pru0.out
```

The script:

1. discovers PRU0 by remoteproc name;
2. stops it if running;
3. installs the ELF into `/lib/firmware/am335x-pru0-fw`;
4. writes the remoteproc firmware selector;
5. starts PRU0;
6. waits for the RPMsg character device.

Inspect state:

```bash
sudo python3 scripts/pru0_ctl.py status
```

## Capability/timebase handshake

```bash
cd boards/beaglebone_black/host
python3 hil_pru_cli.py hello
python3 hil_pru_cli.py time
```

Expected B0 capabilities are:

- `timebase`
- `rpmsg`
- `gpio_loopback`
- `force_safe`
- `watchdog`

## Deterministic GPIO loopback

With the P9_31 -> P9_29 jumper installed:

```bash
python3 hil_pru_cli.py loopback --delay-us 1000 --width-us 1000 --timeout-us 5000
```

The PRU itself schedules the output transition and samples the return input. Linux only submits the command and receives the timestamps.

Record at minimum:

- requested start tick;
- observed input rise tick;
- observed input fall tick;
- measured rise latency;
- measured pulse width;
- firmware git SHA / repository commit;
- kernel version and BBB revision.

Repeat the same measurement with a logic analyzer/oscilloscope before closing B0.

## Safe state

B0 drives the temporary PRU output LOW:

- before RPMsg is ready;
- after each loopback test;
- on explicit `safe` command;
- whenever the host watchdog expires.

Remoteproc stop/reset electrical behavior still requires physical qualification. The protected final DUT adapter must not rely only on PRU firmware for hazardous-state prevention.

## B0 completion still requiring hardware evidence

Repository code can establish the implementation and automated software checks, but #11 stays open until the real BBB demonstrates:

- build/deploy/restart on the target image;
- RPMsg HELLO/TIME exchange;
- P9_31 -> P9_29 loopback timestamps;
- logic-analyzer timing comparison;
- boot/stop/host-loss safe-state behavior.
