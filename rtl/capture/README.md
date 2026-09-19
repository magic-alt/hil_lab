# Capture RTL

Canonical Architecture v2 home for deterministic acquisition and measurement RTL.

Current sources:

- `pwm_capture.v` — asynchronous PWM synchronization and period/high/low timing;
- `pwm_complementary_monitor.v` — complementary-pair dead-time/overlap monitoring;
- `abz_encoder_capture.v` — x4 quadrature capture with illegal-transition latch;
- `ssi_encoder_master_capture.v` — SSI-style master clock and synchronous data capture.

Stimulus/generator counterparts intentionally remain under legacy `rtl/pwm/` and `rtl/encoder/` until Phase 3 migrates that family atomically.
