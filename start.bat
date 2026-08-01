@echo off
title TUX*BERT
cd /d "%~dp0"

rem Find a real Python: try "python" on PATH first, then the "py" launcher
rem (which the python.org installer registers even when the "Add python.exe
rem to PATH" checkbox was left unticked). Using --version also rejects the
rem fake Microsoft Store "python" stub.
set "PY=python"
python --version >nul 2>nul
if not errorlevel 1 goto :found
set "PY=py -3"
py -3 --version >nul 2>nul
if not errorlevel 1 goto :found

echo Python was not found.
echo.
echo If you JUST installed it: close this window and run start.bat again
echo from a fresh window - the PATH only updates for new windows.
echo.
echo Otherwise install Python 3 from https://www.python.org/downloads/
echo and IMPORTANT: tick "Add python.exe to PATH" on the first screen
echo of the installer.
pause
exit /b 1

:found
%PY% -c "import pyray" >nul 2>nul
if errorlevel 1 (
    echo Installing requirements...
    %PY% -m pip install -r requirements.txt
)

%PY% tuxbert.py
if errorlevel 1 pause
