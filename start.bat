@echo off
title TUX*BERT
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH. Install Python 3 and try again.
    pause
    exit /b 1
)

python -c "import pyray" >nul 2>nul
if errorlevel 1 (
    echo Installing requirements...
    python -m pip install -r requirements.txt
)

python tuxbert.py
if errorlevel 1 pause
