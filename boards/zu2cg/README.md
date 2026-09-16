# ZU2CG reference integration

This directory is the home for the first physical target.

The reusable core does not assume a particular ZU2CG carrier because oscillator pins, PMOD/FMC routing, I/O bank voltages and connector assignments vary by board.

Before adding XDC constraints, record:

- exact board/vendor/model/revision;
- PL reference-clock frequency and pin;
- reset source and polarity;
- I/O bank voltage for each HIL connector;
- PWM input pins;
- ABZ/SPI/DIO output pins;
- any level-shifter direction-control pins.

Recommended future board wrapper:

```text
boards/zu2cg/
├── rtl/zu2cg_hil_top.v
├── constraints/<exact-board>.xdc
├── scripts/create_project.tcl
└── README.md
```

Do not commit a generated Vivado project. Keep the build reproducible from source RTL, XDC and Tcl.
