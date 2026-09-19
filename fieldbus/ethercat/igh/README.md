# IgH EtherCAT

Track D1 (#48) uses IgH for the long-running Linux EtherCAT master path.

Controller v1 provides `IghEthercatCli` for evidence-preserving `ethercat master` and `ethercat slaves` probes. These commands validate installation/topology visibility only.

**Do not treat a successful CLI probe or PREEMPT_RT kernel as proof of real-time EtherCAT quality.** Physical qualification still requires cycle-period/jitter, WKC and Distributed Clocks/SYNC0 evidence under representative load.
