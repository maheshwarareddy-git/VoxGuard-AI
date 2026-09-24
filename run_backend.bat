@echo off
title VoxGuard FastAPI Backend (Port 8000)
cd /d "%~dp0backend"
echo ========================================================
echo   Starting VoxGuard AMVTF Backend on http://127.0.0.1:8000
echo ========================================================
if exist "%~dp0python-runtime\python.exe" (
    "%~dp0python-runtime\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
) else (
    python -m uvicorn main:app --host 127.0.0.1 --port 8000
)
pause
