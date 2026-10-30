@echo off
title CSI Forensic AI - Frontend Workstation
color 0B

echo ========================================================
echo       CSI FORENSIC AI - FRONTEND CLIENT LAUNCHER
echo ========================================================
echo.

cd /d "%~dp0"

set "TARGET_URL=http://127.0.0.1:5000"

echo [INFO] Checking if Forensic Backend is active on port 5000...

netstat -ano 2>nul | findstr /r ":5000\>" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 (
    echo [SUCCESS] Backend is already active and running!
    goto OPEN_BROWSER
)

echo [NOTICE] Backend server is not running yet.
echo [INFO] Launching backend server in a dedicated window...
start "CSI Forensic AI - Backend Server" cmd /k "start_backend.bat"

echo [INFO] Waiting for backend to initialize and bind port 5000...
set "MAX_RETRIES=35"
set "COUNT=0"

:CHECK_PORT
netstat -ano 2>nul | findstr /r ":5000\>" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 goto OPEN_BROWSER

set /a COUNT+=1
if %COUNT% geq %MAX_RETRIES% goto OPEN_BROWSER

powershell -NoProfile -Command "Start-Sleep -Seconds 1"
echo   [...] Connecting to neural models and database... (%COUNT%s)
goto CHECK_PORT

:OPEN_BROWSER
echo.
echo [INFO] Opening Forensic Workstation in default browser:
echo        %TARGET_URL%
echo.

start "" "%TARGET_URL%"

echo ========================================================
echo [DONE] Forensic Workstation frontend launched!
echo ========================================================
powershell -NoProfile -Command "Start-Sleep -Seconds 4"
exit /b 0
