@echo off
setlocal
REM ===================================================================
REM  randomize.bat - double-click to generate a new randomized ROM.
REM  Requires WSL with the build tools installed (one-time setup).
REM    Double-click            -> random seed
REM    randomize.bat 12345     -> specific seed (from a cmd window)
REM ===================================================================

REM Folder this .bat lives in, without the trailing backslash.
set "PROJ=%~dp0"
if "%PROJ:~-1%"=="\" set "PROJ=%PROJ:~0,-1%"

echo ============================================================
echo   PokeRando  -  building a randomized ROM
echo ============================================================
echo   Folder: %PROJ%
echo.

REM Make sure the launcher script is actually here (and not "new_seed.sh.txt").
if not exist "%PROJ%\new_seed.sh" (
  echo ERROR: new_seed.sh was not found in this folder.
  echo.
  echo Files currently here:
  dir /b "%PROJ%"
  echo.
  echo Fix: put new_seed.sh in the SAME folder as randomize.bat, and make sure
  echo it is named exactly "new_seed.sh"  ^(not "new_seed.sh.txt"^).
  echo.
  pause
  exit /b 1
)

echo Starting the build in WSL. Files will scroll by while it compiles -
echo that IS the progress bar. The first build takes a few minutes;
echo later seeds are much faster.
echo.

REM Run in this folder; strip Windows line-endings first so WSL can read it.
wsl --cd "%PROJ%" bash -c "sed -i 's/\r$//' new_seed.sh hen_randomizer.py 2>/dev/null; bash new_seed.sh %1"
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo ============================================================
  echo   DONE^!  Your ROM is in the 'roms' folder.
  echo ============================================================
) else (
  echo ============================================================
  echo   Something went wrong - scroll up to read the error.
  echo ============================================================
)
pause
endlocal
