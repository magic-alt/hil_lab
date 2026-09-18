#!/bin/sh
set -eu

if ! command -v config-pin >/dev/null 2>&1; then
  echo "ERROR: config-pin not found; use a BeagleBoard Debian image with cape-universal support" >&2
  exit 2
fi

# B1 six-channel direct PRU0 input map.
# Logical order is UH, UL, VH, VL, WH, WL.
config-pin P9_29 pruin
config-pin P9_30 pruin
config-pin P9_28 pruin
config-pin P9_27 pruin
config-pin P8_16 pruin
config-pin P8_15 pruin

echo "B1 PWM input pinmux configured:"
for pin in P9_29 P9_30 P9_28 P9_27 P8_16 P8_15; do
  config-pin -q "$pin"
done

cat <<'MSG'

Logical PWM input map:
  UH -> P9_29 -> PRU0 R31[1]
  UL -> P9_30 -> PRU0 R31[2]
  VH -> P9_28 -> PRU0 R31[3]
  VL -> P9_27 -> PRU0 R31[5]
  WH -> P8_16 -> PRU0 R31[14]
  WL -> P8_15 -> PRU0 R31[15]

Use only 3.3 V logic-level signals or a reviewed level-shift/buffer adapter.
Do not connect raw BBB pins to gate-driver power, motor phases, brake power or DC bus.
MSG
