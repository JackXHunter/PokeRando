@echo off
REM ===================================================================
REM  randomize.bat - double-click to generate a new randomized ROM.
REM  Requires WSL with the build tools installed (one-time setup):
REM    sudo apt install build-essential binutils-arm-none-eabi \
REM         gcc-arm-none-eabi git libpng-dev pkg-config python3
REM
REM  Double-click            -> random seed
REM  randomize.bat 12345     -> specific seed (from a cmd window)
REM ===================================================================
pushd "%~dp0"
echo Generating a randomized ROM via WSL (this can take a few minutes)...
echo.

REM Launch WSL in this folder; strip any Windows CR line-endings from the
REM shell scripts first, then run the launcher. %1 is the optional seed.
wsl bash -c "sed -i 's/\r$//' new_seed.sh 2>/dev/null; bash new_seed.sh %1"

echo.
if errorlevel 1 (
  echo Something went wrong - see the messages above.
) else (
  echo Done^! Your ROM is in the 'roms' folder.
)
popd
pause
