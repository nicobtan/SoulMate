@echo off
echo Starting Soulmate...
echo.

set PYTHON_EXE=.\.venv\Scripts\python.exe

if not exist %PYTHON_EXE% (
    echo Python executable not found in virtual environment.
    pause
    exit /b 1
)

%PYTHON_EXE% main.py

echo.
echo Application window closed.
pause
