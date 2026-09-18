@echo off
setlocal EnableExtensions EnableDelayedExpansion
set "PROJECT=%~dp0hil_pwm_stimulus.uvprojx"
set "UV4=%KEIL_UVISION%"
if not defined UV4 if exist "C:\Keil_v5\UV4\UV4.exe" set "UV4=C:\Keil_v5\UV4\UV4.exe"
if not defined UV4 ( echo ERROR: set KEIL_UVISION to UV4.exe & exit /b 2 )
set TARGETS=20k_50_600ns 20k_50_700ns 20k_50_800ns 20k_5_700ns 20k_25_700ns 20k_75_700ns 20k_95_700ns
set FAILED=0
if not exist "%~dp0Logs" mkdir "%~dp0Logs"
for %%T in (%TARGETS%) do (
  echo === Building %%T ===
  "%UV4%" -b "%PROJECT%" -t "%%T" -j0 -o "%~dp0Logs\%%T.log"
  if errorlevel 1 set FAILED=1
)
if not "%FAILED%"=="0" exit /b 1
exit /b 0
