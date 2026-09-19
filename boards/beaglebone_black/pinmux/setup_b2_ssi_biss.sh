#!/bin/sh
set -eu

command -v config-pin >/dev/null 2>&1 || {
    echo "ERROR: config-pin not found" >&2
    exit 2
}

# SSI / BiSS-C master-clock input plus encoder-data output.
config-pin P8_45 pruin
config-pin P8_46 pruout

echo "B2 SSI/BiSS serial pinmux configured:"
config-pin -q P8_45
config-pin -q P8_46

cat <<'EOF'

Serial map:
  MA/CLK -> P8_45 -> PRU1 R31[0] input
  SLO/DATA <- P8_46 <- PRU1 R30[1] output

P8_45/P8_46 overlap the BBB LCD/HDMI pin group. Run headless and keep these
modes mutually exclusive with ABZ/Hall output mode.

Raw BBB pins are 3.3 V single-ended. Real SSI/BiSS-C differential links require
a reviewed RS-422/level-shift adapter before connection to a servo DUT.
EOF
