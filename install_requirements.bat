@echo off
title TUX*BERT - install requirements
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found on PATH.
    echo Install Python 3 from https://www.python.org/downloads/ and re-run this script.
    pause
    exit /b 1
)

echo Installing TUX*BERT requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Install failed - see the error above.
    pause
    exit /b 1
)

echo.
echo Done! Run start.bat to play.
pause
