@echo off
title VoxGuard Next.js Frontend (Port 3000)
cd /d "%~dp0echoguard"
echo ========================================================
echo   Starting VoxGuard Web Dashboard on http://localhost:3000
echo ========================================================
npm run dev
pause
