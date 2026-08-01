@echo off
title TUX*BERT - install requirements
cd /d "%~dp0"

rem Find a real Python: try "python" on PATH first, then the "py" launcher
rem (registered by the python.org installer even without the PATH checkbox).
set "PY=python"
python --version >nul 2>nul
if not errorlevel 1 goto :found
set "PY=py -3"
py -3 --version >nul 2>nul
if not errorlevel 1 goto :found

echo Python was not found.
echo.
echo If you JUST installed it: close this window and run this script again
echo from a fresh window - the PATH only updates for new windows.
echo.
echo Otherwise install Python 3 from https://www.python.org/downloads/
echo and IMPORTANT: tick "Add python.exe to PATH" on the first screen
echo of the installer.
pause
exit /b 1

:found
echo Using: & %PY% --version
echo Installing TUX*BERT requirements...
%PY% -m pip install --upgrade pip
%PY% -m pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo Install failed - see the error above.
    pause
    exit /b 1
)

echo.
echo Done! Run start.bat to play.
pause
