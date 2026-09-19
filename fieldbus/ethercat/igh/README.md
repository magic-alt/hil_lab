# IgH EtherCAT

Track D1 (#48) uses IgH for the long-running Linux EtherCAT master path.

Controller v1 provides `IghEthercatCli` for evidence-preserving `ethercat master` and `ethercat slaves` probes. These commands validate installation/topology visibility only.

**Do not treat a successful CLI probe or PREEMPT_RT kernel as proof of real-time EtherCAT quality.** Physical qualification still requires cycle-period/jitter, WKC and Distributed Clocks/SYNC0 evidence under representative load.


`cia402_cycle.c` is the hardware qualification executable. It defaults to observe-only (`enable_drive=0`) and emits JSON WKC/DC/jitter evidence. Explicit drive enable is required for CiA402 Operation Enabled testing.
