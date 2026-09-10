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

:: Tu dong kiem tra va cai dat thu vien neu chua co
python -c "import easyocr" >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [INFO] Phat hien chua co thu vien Auto-Claim. Dang tu dong cai dat...
    python -m pip install -r auto_claim/requirements.txt
    echo [OK] Cai dat hoan tat!
    echo.
)

python main.py
pause
