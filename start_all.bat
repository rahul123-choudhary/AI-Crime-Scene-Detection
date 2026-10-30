@echo off
title CSI Forensic AI - Full System Launcher
color 0E

echo ========================================================
echo        CSI FORENSIC AI - FULL SYSTEM LAUNCHER
echo ========================================================
echo.
echo [1/2] Starting Forensic AI Backend Server in dedicated window...
echo.

cd /d "%~dp0"

:: Launch backend in a dedicated command window (stays open with /k)
start "CSI Forensic AI - Backend Server" cmd /k "start_backend.bat"

echo [2/2] Connecting to Neural Models and Database Services...
echo Waiting for backend server to become available on port 5000...
echo.

:: Smart Port Polling Loop (waits until port 5000 is LISTENING, up to 35s)
set "MAX_RETRIES=35"
set "COUNT=0"

:CHECK_PORT
netstat -ano 2>nul | findstr /r ":5000\>" | findstr "LISTENING" >nul 2>&1
if %errorlevel% equ 0 goto LAUNCH_BROWSER

set /a COUNT+=1
if %COUNT% geq %MAX_RETRIES% goto TIMEOUT_ERROR

powershell -NoProfile -Command "Start-Sleep -Seconds 1"
echo   [...] Initializing database and AI neural weights... (%COUNT%s)
goto CHECK_PORT

:LAUNCH_BROWSER
echo.
echo ========================================================
echo [SUCCESS] Forensic AI Backend Server is live!
echo [INFO] Opening Forensic Workstation in default browser...
echo        http://127.0.0.1:5000
echo ========================================================
echo.

start "" "http://127.0.0.1:5000"

echo [DONE] Forensic Workstation launched successfully.
echo You can close this window now. (Leave the Backend Server window open).
echo.
powershell -NoProfile -Command "Start-Sleep -Seconds 4"
exit /b 0

:TIMEOUT_ERROR
echo.
echo ========================================================
echo [WARNING] Backend took longer than expected to bind port 5000.
echo Please inspect the "CSI Forensic AI - Backend Server" window
echo to verify initialization logs or errors.
echo.
echo Attempting to launch browser anyway: http://127.0.0.1:5000
echo ========================================================
start "" "http://127.0.0.1:5000"
pause
