# Raspberry Pi 4/5 HIL Controller

Track D uses Raspberry Pi as a Linux control plane, not as a deterministic PWM/encoder backend.

Planned services:

- pytest and common host.hil API;
- labgrid exporter/resource control;
- IgH EtherCAT master and SOEM diagnostics;
- SocketCAN/CANopen;
- optional ROS2/ros2_control;
- artifact/log collection and remote bench service lifecycle.

PREEMPT_RT is optional and must be qualified with measured cyclictest and fieldbus cycle/DC/WKC evidence. Ordinary Linux GPIO timing must never be advertised as a deterministic backend capability.

See #47, #48 and #49.
