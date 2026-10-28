@echo off
title CSI Forensic AI - Backend Server
color 0A

echo ========================================================
echo        CSI FORENSIC AI - BACKEND SERVER LAUNCHER
echo ========================================================
echo.

:: Navigate to script directory
cd /d "%~dp0"

:: Check virtual environment
if exist "venv\Scripts\python.exe" (
    echo [INFO] Virtual environment detected: .\venv
    set "PYTHON_EXE=venv\Scripts\python.exe"
) else (
    echo [WARNING] Virtual environment not found in .\venv!
    echo [INFO] Trying system Python...
    set "PYTHON_EXE=python"
)

:: Verify Python executable
"%PYTHON_EXE%" --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] Python was not found!
    echo Please install Python 3.10+ or set up the virtual environment.
    echo.
    pause
    exit /b 1
)

echo [INFO] Launching Forensic AI Backend Server on port 5000...
echo [INFO] API and Web interface will be available at:
echo        http://127.0.0.1:5000
echo.
echo Press Ctrl+C in this window to stop the server.
echo ========================================================
echo.

"%PYTHON_EXE%" run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server exited with an error.
    pause
)
