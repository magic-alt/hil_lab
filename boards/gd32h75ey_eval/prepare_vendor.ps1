param(
  [Parameter(Mandatory=$true)][string]$SourceRoot
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vendor = Join-Path $Root "Vendor"

function Copy-Unique([string]$Name, [string]$Destination) {
  $matches = Get-ChildItem -Path $SourceRoot -Recurse -File -Filter $Name
  if ($matches.Count -eq 0) { throw "Missing $Name under $SourceRoot" }
  $selected = $matches | Select-Object -First 1
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  Copy-Item $selected.FullName (Join-Path $Destination $Name) -Force
  Write-Host ("Copied " + $selected.FullName)
}

$Cmsis = Join-Path $Vendor "CMSIS"
$DeviceInc = Join-Path $Vendor "CMSIS/GD/GD32H75E/Include"
$DeviceSrc = Join-Path $Vendor "CMSIS/GD/GD32H75E/Source"
$DeviceArm = Join-Path $Vendor "CMSIS/GD/GD32H75E/Source/ARM"
$SplInc = Join-Path $Vendor "GD32H75E_standard_peripheral/Include"
$SplSrc = Join-Path $Vendor "GD32H75E_standard_peripheral/Source"

foreach ($name in @("core_cm7.h","cmsis_version.h","cmsis_compiler.h","cmsis_armcc.h","cmsis_armclang.h","cmsis_armclang_ltm.h","cmsis_gcc.h","cmsis_iccarm.h","cmsis_ccs.h","cmsis_csm.h","mpu_armv7.h","cachel1_armv7.h")) {
  $matches = Get-ChildItem -Path $SourceRoot -Recurse -File -Filter $name
  if ($matches.Count -gt 0) {
    New-Item -ItemType Directory -Force -Path $Cmsis | Out-Null
    Copy-Item ($matches | Select-Object -First 1).FullName (Join-Path $Cmsis $name) -Force
  }
}

Copy-Unique "gd32h75e.h" $DeviceInc
Copy-Unique "system_gd32h75e.h" $DeviceInc
Copy-Unique "system_gd32h75e.c" $DeviceSrc
Copy-Unique "startup_gd32h75e.s" $DeviceArm

foreach ($name in @("gd32h75e_gpio.h","gd32h75e_rcu.h","gd32h75e_timer.h")) { Copy-Unique $name $SplInc }
foreach ($name in @("gd32h75e_gpio.c","gd32h75e_rcu.c","gd32h75e_timer.c")) { Copy-Unique $name $SplSrc }

Write-Host "GD32H75E vendor subset prepared."
