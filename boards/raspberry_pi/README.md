# Raspberry Pi 4/5 HIL Controller

Track D uses Raspberry Pi as a Linux control plane, not as a deterministic PWM/encoder backend.

Controller v1 adds:

- OS/kernel/NIC/tool environment probing;
- PREEMPT_RT **hint detection** only — qualification still requires measured cyclictest evidence;
- IgH `ethercat` CLI status/slave-scan evidence adapter;
- configurable SOEM `slaveinfo` evidence adapter;
- real Python-standard-library SocketCAN CAN_RAW transport;
- CANopen NMT command and heartbeat primitives;
- bench resource inventory and non-blocking Linux resource lock.

Still pending physical D0/D1 qualification:

- cyclictest under idle/stress on the selected Pi image;
- 1 ms EtherCAT cycle, WKC, DC/SYNC0 and jitter evidence;
- real CAN interface/vcan execution in controller CI;
- CANopen SDO/PDO/CiA402 implementation/qualification;
- service startup/reboot/network-loss recovery.

Ordinary Linux GPIO timing must never be advertised as a deterministic backend capability.

See #47, #48 and #49.


Controller v2 adds cyclictest qualification parsing, IgH/SOEM 1 ms cycle executables, CANopen SDO/EMCY/CiA402 and labgrid/pytest session safety. These tools create the evidence; the repository still does not mark physical latency/WKC/DC criteria passed until run on the selected Pi/NIC/DUT.
