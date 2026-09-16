# Verification Strategy

## G0 software-only gate

`make verify` performs four independent checks:

1. `policy` — repository-specific RTL-language and file checks;
2. `compile` — elaborates the reusable top with Icarus Verilog;
3. `test` — runs self-checking Verilog simulations;
4. `lint` — runs Verilator lint in Verilog-2005 mode.

Current smoke simulations cover:

- PWM period/high/low measurement;
- complementary dead-time and fault latching;
- ABZ transition/index generation;
- SPI mode-0 serialization and bit-flip injection;
- timestamped masked DIO update.

## Hardware validation ladder

Simulation success is not equivalent to physical-HIL validation. G0 should progress through:

```text
RTL simulation
    -> FPGA internal/PMOD loopback
    -> external logic-level loopback
    -> servo DUT digital interfaces
    -> DAC evaluation board
    -> closed-loop controller HIL
```

Record board revision, FPGA clock frequency, DUT firmware commit and wiring/adapter revision for every hardware result.
