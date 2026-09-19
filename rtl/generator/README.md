# Generator RTL

Canonical Architecture v2 home for deterministic stimulus and sensor emulation RTL.

Current sources:

- `pwm_complementary_generator.v` — complementary PWM stimulus with configurable period/high/dead time;
- `abz_encoder_emulator.v` — deterministic quadrature/index generation;
- `ssi_encoder_emulator.v` — SSI-style clock-slave position-word emulation;
- `spi_encoder_emulator.v` — SPI mode-0 sensor/encoder response and deterministic bit corruption.

Hall/BiSS-C and richer protocol generators should be added here rather than recreating legacy `rtl/pwm/` or `rtl/encoder/` trees.
