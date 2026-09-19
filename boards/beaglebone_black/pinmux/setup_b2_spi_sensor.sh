#!/bin/sh
set -eu

command -v config-pin >/dev/null 2>&1 || {
    echo "ERROR: config-pin not found" >&2
    exit 2
}

# SPI-style sensor emulator, mode-0 baseline.
config-pin P8_45 pruin
config-pin P8_46 pruout
config-pin P8_43 pruin
config-pin P8_44 pruin

echo "B2 SPI-style sensor pinmux configured:"
config-pin -q P8_45
config-pin -q P8_46
config-pin -q P8_43
config-pin -q P8_44

cat <<'EOF'

SPI-style map:
  SCLK -> P8_45 -> PRU1 R31[0]
  MISO <- P8_46 <- PRU1 R30[1]
  CS_n -> P8_43 -> PRU1 R31[2]
  MOSI -> P8_44 -> PRU1 R31[3]

This is a generic mode-0 command/response baseline. It does not claim
compatibility with a named encoder IC until that device protocol is added.

Use only 3.3 V logic or a reviewed adapter.
EOF
