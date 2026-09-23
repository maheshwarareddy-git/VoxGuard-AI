@echo off
title VoxGuard Launcher
echo ========================================================
echo   Launching VoxGuard Enterprise Services...
echo ========================================================
echo [1/2] Launching Backend on port 8000...
start "VoxGuard Backend (Port 8000)" cmd /k "cd /d "%~dp0backend" && "%~dp0python-runtime\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
echo [2/2] Launching Frontend on port 3000...
start "VoxGuard Frontend (Port 3000)" cmd /k "cd /d "%~dp0echoguard" && npm run dev"
echo.
echo Both servers have been launched!
echo - Web Dashboard: http://localhost:3000
echo - Swagger Docs:  http://127.0.0.1:8000/docs
echo.
