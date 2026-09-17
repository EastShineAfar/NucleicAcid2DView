@echo off
REM ============================================================
REM  NAView structure drawing GUI - Windows launcher
REM
REM  Double-click this file.  Everything it needs is inside this
REM  folder, so the whole "naview" folder can be copied to another
REM  computer (which only needs Python 3.8+ with tkinter -- the
REM  official python.org installer includes tkinter by default).
REM
REM  This .cmd is deliberately ASCII-only: cmd.exe parses batch
REM  files with the OEM codepage, so non-ASCII text would break it.
REM ============================================================
setlocal
cd /d "%~dp0"

set "PYEXE="
for %%P in (pythonw.exe python.exe) do (
    if not defined PYEXE (
        where %%P >nul 2>&1 && set "PYEXE=%%P"
    )
)
if not defined PYEXE (
    where py.exe >nul 2>&1 && set "PYEXE=py.exe -w"
)

if not defined PYEXE (
    echo ============================================================
    echo  Python was not found on this computer.
    echo ============================================================
    echo.
    echo  Install Python 3.8 or newer from https://www.python.org/downloads/
    echo  and keep the default option "tcl/tk and IDLE" ticked, then run
    echo  this file again.
    echo.
    pause
    exit /b 1
)

start "" %PYEXE% "%~dp0gui.py"
exit /b 0
