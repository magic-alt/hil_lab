# Bench resources

Physical HIL resources are versioned independently from test logic.

`BenchResource` records:

- resource ID;
- Linux controller;
- deterministic HIL backend;
- DUT identity;
- protected adapter revision;
- optional fieldbus interface.

`ResourceLock` supplies a local non-blocking `flock` guard beneath future labgrid allocation so two pytest processes cannot silently drive the same bench.

`servo_bench.example.json` is an inventory example, not evidence of physical qualification.
