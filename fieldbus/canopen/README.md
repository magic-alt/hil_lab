# CAN / CANopen

Track D1 (#48) Controller v1 provides:

- real Linux CAN_RAW transport through Python `socket.AF_CAN` / `CAN_RAW`;
- classical 11-bit CAN frame pack/unpack;
- CANopen NMT command frame generation;
- heartbeat/boot-up state parsing.

Current scope is intentionally small. SDO/PDO, heartbeat supervision, EMCY, CiA402 and bus-off/recovery regression remain D1 follow-up work and must be verified on `vcan` and physical CAN before being marked complete.


Controller v2 adds expedited SDO upload/download, abort decoding, EMCY, heartbeat wait and an SDO-based CiA402 enable/quick-stop/disable-voltage state machine. Device-specific PDO layouts remain explicit DUT configuration.
