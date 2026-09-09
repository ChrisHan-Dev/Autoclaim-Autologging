@echo off
title SOP Auto-Logging (Administrator)
cd /d "%~dp0"

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [INFO] Dang yeu cau quyen Administrator...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"\"%~dpnx0\"\"' -Verb RunAs"
    exit /b
)

echo =======================================================
echo   SOP AUTO-LOGGING - RUNNING AS ADMINISTRATOR
echo =======================================================
python sop_main.py
pause
