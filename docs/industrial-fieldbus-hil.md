# Raspberry Pi industrial fieldbus qualification

This layer separates **software implementation** from **physical qualification evidence**.

## IgH EtherCAT

`fieldbus/ethercat/igh/cia402_cycle.c` is a real IgH/ecrt cyclic master for one CiA402 servo.

It configures standard 0x1600/0x1A00 PDOs, Distributed Clocks, a fixed cycle, WKC monitoring and host wake-up jitter measurement. It prints one JSON result record containing cycle count, WKC quality, jitter/deadline metrics, statusword and Operation Enabled dwell.

Safety rule: the program defaults to `enable_drive=0`. With that default it writes controlword 0 and is intended for topology/DC/WKC/jitter qualification. Passing `enable_drive=1` explicitly activates the CiA402 state machine and must only be done on a mechanically safe bench.

Build on the Pi/IgH host:

~~~bash
cd fieldbus/ethercat/igh
make
sudo ./cia402_cycle 0 0xVENDOR 0xPRODUCT 1000 30 8 0x300 0
~~~

## SOEM

`fieldbus/ethercat/soem/soem_cycle.c` performs a generic OP-state process-data cycle and reports expected/actual WKC, DC time and host jitter. It intentionally does not assume a CiA402 PDO layout.

## CANopen

Controller v2 implements:

- NMT and heartbeat;
- expedited SDO upload/download (1..4 bytes) and abort decoding;
- EMCY parsing;
- CiA402 state decoding and controlword progression;
- a safe SDO-based `CanopenCiA402Node` bring-up path;
- SocketCAN remains the real Linux transport.

PDO mapping is device configuration, not a universal default. Device-specific RPDO/TPDO maps should be added only with the DUT object dictionary.

## labgrid + pytest

`LabgridPlaceLease` provides acquire/show/release over a configured labgrid place. `ServoHilSession` composes labgrid allocation, local resource locking and mandatory backend FORCE_SAFE on entry/exit.

Hardware-only tests live under `tests/hil` and do not run in cloud CI. Use:

~~~bash
python tools/run_hil_suite.py lab/resources/servo_bench.json
~~~

## Evidence required to close D0/D1/D2

A physical qualification artifact should retain:

- Pi model, kernel, PREEMPT_RT state and cyclictest result;
- NIC driver/interface and EtherCAT master version;
- cycle period, max/mean absolute jitter, deadline misses;
- expected/actual WKC and bad-WKC count;
- DC/SYNC0 configuration;
- CiA402 mode/status/control transitions if drive enable is used;
- CAN interface bitrate, SDO/heartbeat/EMCY evidence;
- resource inventory and adapter revision;
- exact DUT firmware/bitstream commit.
