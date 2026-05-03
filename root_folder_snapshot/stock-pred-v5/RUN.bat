@echo off
chcp 65001 >nul
title STOCK·PRED v5.0 — Setup ^& Run
color 0B

echo.
echo  ============================================
echo   STOCK·PRED v5.0  —  ML Dashboard
echo   Dual-Market: US + KRX
echo  ============================================
echo.

REM --- node check ---
where node >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo  [X] Node.js not found.
    echo      Install LTS from: https://nodejs.org/
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('node -v') do set NODEVER=%%v
echo  [OK] Node %NODEVER% detected
echo.

REM --- install if needed ---
if not exist "node_modules" (
    echo  [..] Installing dependencies (first run only)...
    echo.
    call npm install
    if %ERRORLEVEL% NEQ 0 (
        echo.
        echo  [X] npm install failed.
        pause
        exit /b 1
    )
    echo.
    echo  [OK] Dependencies installed
    echo.
)

echo  [..] Starting dev server at http://localhost:5173
echo       Browser opens automatically.
echo       Press Ctrl+C to stop.
echo.
call npm run dev
pause
