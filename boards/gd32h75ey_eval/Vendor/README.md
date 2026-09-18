# GD32H75E vendor dependency

This directory is intentionally not populated in git.

Use the official **GD32H75E Firmware Library 1.3.0** package, extract it, then
run from PowerShell:

    ..\prepare_vendor.ps1 -SourceRoot "D:\SDK\GD32H75E_Firmware_Library"

The script copies only the CMSIS/device/SPL files required by the PWM stimulus
into this Vendor directory.

The Keil project also expects the current GigaDevice GD32H75E DFP installed in
Keil.
