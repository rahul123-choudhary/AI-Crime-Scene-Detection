       @echo off
title CSI Forensic AI - Full System Launcher
color 0E

echo ========================================================
echo        CSI FORENSIC AI - FULL SYSTEM LAUNCHER
echo ========================================================
echo.
echo Starting Backend Server and Frontend Workstation...
echo.

cd /d "%~dp0"

:: Start backend in a dedicated window
start "CSI Forensic AI - Backend Server" cmd /c "start_backend.bat"

:: Wait 3 seconds for Flask to bind port 5000
echo [INFO] Initializing Forensic AI Neural Engine & Server...
powershell -Command "Start-Sleep -Seconds 3"

:: Launch browser frontend
echo [INFO] Opening Frontend Workstation in browser...
start "" "http://127.0.0.1:5000"

echo.
echo ========================================================
echo  System is running at http://127.0.0.1:5000
echo  - Backend log window is running in the background.
echo  - Close the Backend window when you want to stop the server.
echo ========================================================
timeout /t 5 >nul
