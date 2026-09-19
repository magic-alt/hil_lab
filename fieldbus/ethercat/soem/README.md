# SOEM

Track D1 (#48) uses SOEM for lightweight EtherCAT discovery/diagnostics and focused regression utilities.

Controller v1 provides a configurable `SoemSlaveInfo` wrapper around the SOEM `slaveinfo` example. The path is configurable because SOEM installations do not provide one universal executable location/name.

Cyclic servo control remains a later physical qualification item; this adapter does not claim real-time master performance.


`soem_cycle.c` provides an independent generic OP-state WKC/DC/jitter qualification path without assuming a CiA402 PDO mapping.
