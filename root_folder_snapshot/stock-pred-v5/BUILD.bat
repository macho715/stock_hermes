@echo off
chcp 65001 >nul
title STOCK·PRED v5.0 — Build
color 0E

echo.
echo  Building production bundle...
echo.

if not exist "node_modules" (
    call npm install
)

call npm run build
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [X] Build failed.
    pause
    exit /b 1
)

echo.
echo  [OK] Build complete -> dist\
echo  [..] Starting preview at http://localhost:4173
echo.
call npm run preview
pause
