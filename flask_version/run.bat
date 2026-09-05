@echo off
setlocal
title Innovation Portfolio Dashboard
cd /d "%~dp0"

echo ============================================
echo   Innovation Portfolio Dashboard - Setup
echo ============================================
echo.

rem --- find a working Python command (python, then py, then python3) ---
set PYCMD=
python --version >nul 2>&1 && set PYCMD=python
if not defined PYCMD (
    py --version >nul 2>&1 && set PYCMD=py
)
if not defined PYCMD (
    python3 --version >nul 2>&1 && set PYCMD=python3
)

if not defined PYCMD (
    echo [ERROR] Python was not found on this computer.
    echo.
    echo Please install Python from https://www.python.org/downloads/
    echo During install, tick the box "Add python.exe to PATH".
    echo Then double-click this file again.
    echo.
    pause
    exit /b 1
)

echo Using: %PYCMD%
%PYCMD% --version
echo.

echo Installing required packages (this can take a minute the first time)...
%PYCMD% -m pip install --quiet --disable-pip-version-check flask pandas openpyxl
if errorlevel 1 (
    echo.
    echo [ERROR] Package install failed. Trying again with more detail...
    %PYCMD% -m pip install flask pandas openpyxl
    if errorlevel 1 (
        echo.
        echo [ERROR] Still failing. Copy the red text above and send it back for help.
        pause
        exit /b 1
    )
)

echo.
echo Packages OK. Starting the dashboard...
echo Opening http://127.0.0.1:5057 in your browser.
echo Keep this window open while you use the dashboard.
echo.

start "" http://127.0.0.1:5057
%PYCMD% app.py

echo.
echo The dashboard has stopped.
pause
