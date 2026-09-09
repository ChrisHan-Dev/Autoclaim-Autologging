@echo off
title AutoClaim Teleops (Administrator)
cd /d "%~dp0"

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Dang yeu cau quyen Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo =======================================================
echo   AUTOCLAIM TELEOPS - RUNNING AS ADMINISTRATOR
echo =======================================================
python main.py
pause
