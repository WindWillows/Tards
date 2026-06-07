@echo off
cd /d "%~dp0"

:: Auto-detect Python (py / python / python3)
set PYTHON_CMD=
for %%C in (py python python3) do (
    %%C --version >nul 2>&1
    if not errorlevel 1 (
        set PYTHON_CMD=%%C
        goto :found
    )
)
echo Python not found. Please install Python 3.10+
echo https://www.python.org/downloads/
pause
exit /b 1

:found
echo Using: %PYTHON_CMD%

echo Installing dependencies...
%PYTHON_CMD% -m pip install -r requirements.txt -q
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

echo Starting Tards...
%PYTHON_CMD% Gamestart.py
pause
