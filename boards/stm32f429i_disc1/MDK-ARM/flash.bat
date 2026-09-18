@echo off
setlocal EnableExtensions

set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=20k_50_700ns"

set "HEX=%~dp0Objects\%TARGET%\hil_pwm_%TARGET%.hex"
if not exist "%HEX%" (
    echo ERROR: HEX not found:
    echo   %HEX%
    echo Build target %TARGET% first.
    exit /b 2
)

set "STM32CLI=%STM32_PROGRAMMER_CLI%"
if not defined STM32CLI (
    if exist "C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe" (
        set "STM32CLI=C:\Program Files\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    ) else if exist "C:\Program Files (x86)\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe" (
        set "STM32CLI=C:\Program Files (x86)\STMicroelectronics\STM32Cube\STM32CubeProgrammer\bin\STM32_Programmer_CLI.exe"
    )
)

if not defined STM32CLI (
    echo ERROR: STM32_Programmer_CLI.exe not found.
    echo Install STM32CubeProgrammer or set:
    echo   set STM32_PROGRAMMER_CLI=C:\path\to\STM32_Programmer_CLI.exe
    exit /b 3
)

echo Flashing %TARGET%
echo HEX: %HEX%
"%STM32CLI%" -c port=SWD -w "%HEX%" -v -rst
if errorlevel 1 exit /b 1

echo Flash complete: %TARGET%
exit /b 0
