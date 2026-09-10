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

:: 1. Kiem tra Python tren may
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [THONG BAO] May tinh chua co Python!
    echo Dang thu tu dong cai dat Python 3.12 qua Windows Winget (khoang 30-60 giay)...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    
    :: Cap nhat PATH tam thoi cho session hien tai
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;C:\Program Files\Python312;C:\Program Files\Python312\Scripts;%PATH%"
    
    python --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo.
        echo [CHUA XONG] Khong the tu dong cai dat Python tren may nay.
        echo Vui long cai dat Python thu cong 1 lan duy nhat:
        echo   1. Tai Python tai: https://www.python.org/downloads/
        echo   2. Khi cai dat, NHO TICH VAO O: "Add Python to PATH"
        echo   3. Mo lai file nay sau khi cai xong!
        echo.
        pause
        exit /b
    )
    echo [OK] Da cai dat Python thanh cong!
    echo.
)

:: 2. Tu dong kiem tra va cai dat thu vien neu chua co (chi mat 5 giay)
python -c "import pyautogui" >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [INFO] Phat hien lan dau chay - Dang tu dong cai dat thu vien (5 giay)...
    python -m pip install -r auto_logging/requirements.txt
    echo [OK] Cai dat hoan tat!
    echo.
)

python sop_main.py
pause
