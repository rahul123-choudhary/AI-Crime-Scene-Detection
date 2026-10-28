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

powershell -Command "$tcp = New-Object Net.Sockets.TcpClient; try { $tcp.Connect('127.0.0.1', 5000); $true } catch { $false } finally { $tcp.Dispose() }" > "%TEMP%\csi_port_check.txt" 2>nul
set /p IS_RUNNING=<"%TEMP%\csi_port_check.txt"
del "%TEMP%\csi_port_check.txt" 2>nul

if "%IS_RUNNING%"=="True" (
    echo [SUCCESS] Backend is active and running!
) else (
    echo [NOTICE] Backend server is not running yet.
    echo [INFO] Launching backend server in a background window...
    start "CSI Forensic AI - Backend Server" cmd /c "start_backend.bat"
    echo [INFO] Waiting for backend to initialize...
    powershell -Command "Start-Sleep -Seconds 3"
)

echo [INFO] Opening Forensic Workstation in default browser:
echo        %TARGET_URL%
echo.

start "" "%TARGET_URL%"

echo [DONE] Forensic Workstation frontend launched!
echo You can keep this window or close it.
echo ========================================================
timeout /t 5 >nul
