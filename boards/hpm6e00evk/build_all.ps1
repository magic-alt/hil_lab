param([string]$Generator = "Ninja", [string]$BuildType = "release")
$ErrorActionPreference = "Stop"
if (-not $env:HPM_SDK_BASE) { throw "HPM_SDK_BASE is not set" }
$profiles = @("20k_50_600ns","20k_50_700ns","20k_50_800ns","20k_5_700ns","20k_25_700ns","20k_75_700ns","20k_95_700ns")
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
foreach ($profile in $profiles) {
  $build = Join-Path $root ("build/" + $profile)
  Write-Host ("=== HPM6E00EVK: " + $profile + " ===")
  cmake -S $root -B $build -G $Generator -DBOARD=hpm6e00evk -DHIL_PWM_PROFILE=$profile -DCMAKE_BUILD_TYPE=$BuildType
  cmake --build $build
}
