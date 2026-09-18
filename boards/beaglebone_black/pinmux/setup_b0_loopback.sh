#!/usr/bin/env bash
set -euo pipefail

if ! command -v config-pin >/dev/null 2>&1; then
  echo "ERROR: config-pin not found; use a BeagleBoard Debian image with cape-universal support" >&2
  exit 2
fi

# Temporary B0 validation fixture. This is not the final servo-DUT pin map.
config-pin P9_31 pruout
config-pin P9_25 pruin

echo "B0 loopback pinmux configured:"
config-pin -q P9_31
config-pin -q P9_25
cat <<'MSG'
Connect a short jumper:
  P9_31 (PRU0 R30 bit 0, output) -> P9_25 (PRU0 R31 bit 7, input)
Do not connect these raw pins to 24/48 V or any power-stage node.
MSG
