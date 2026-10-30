@echo off
title CSI Forensic AI - Backend Server
color 0A

echo ========================================================
echo        CSI FORENSIC AI - BACKEND SERVER LAUNCHER
echo ========================================================
echo.

:: Navigate to script directory
cd /d "%~dp0"

:: Set PYTHONPATH to project root
set "PYTHONPATH=%~dp0"

:: Release port 5000 if occupied by stale process
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr /r ":5000\>"') do (
    if not "%%a"=="" (
        echo [INFO] Releasing port 5000 from previous process %%a
        taskkill /F /PID %%a >nul 2>&1
    )
)

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
    echo Please install Python 3.10+ or set up the virtual environment in .\venv.
    echo.
    pause
    exit /b 1
)

echo.
echo [INFO] Initializing Forensic AI Neural Engine and Backend...
echo [INFO] Server will bind to: http://127.0.0.1:5000
echo.
echo ========================================================
echo   BACKEND SERVER LOGS - Press Ctrl+C to stop
echo ========================================================
echo.

"%PYTHON_EXE%" run.py

echo.
echo ========================================================
echo [NOTICE] Backend server stopped.
echo ========================================================
pause
