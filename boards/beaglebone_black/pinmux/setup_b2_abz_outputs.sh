#!/bin/sh
set -eu

need_config_pin() {
    command -v config-pin >/dev/null 2>&1 || {
        echo "ERROR: config-pin not found" >&2
        exit 2
    }
}

need_config_pin

# B2.1 PRU1 direct outputs.
config-pin P8_45 pruout
config-pin P8_46 pruout
config-pin P8_43 pruout

echo "B2 ABZ output pinmux configured:"
config-pin -q P8_45
config-pin -q P8_46
config-pin -q P8_43

cat <<'EOF'

Logical ABZ output map:
  A -> P8_45 -> PRU1 R30[0]
  B -> P8_46 -> PRU1 R30[1]
  Z -> P8_43 -> PRU1 R30[2]

These P8 pins overlap the BBB LCD/HDMI pin group. Run headless and ensure
the active device-tree/cape configuration leaves them available for pruout.

Use only 3.3 V logic-level loads or a reviewed line-driver/level-shift adapter.
EOF
