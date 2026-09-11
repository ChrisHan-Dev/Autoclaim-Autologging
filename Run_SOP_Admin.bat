@echo off
title SOP Auto-Logging (Administrator)
cd /d "%~dp0"

:: 1. Tu dong tim va them duong dan Python vao PATH neu chua co
for %%v in (314 313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%v" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python%%v;%LOCALAPPDATA%\Programs\Python\Python%%v\Scripts;%PATH%"
    )
    if exist "C:\Program Files\Python%%v" (
        set "PATH=C:\Program Files\Python%%v;C:\Program Files\Python%%v\Scripts;%PATH%"
    )
)

:: 2. Kiem tra quyen Administrator
net session >nul 2>&1
if %errorLevel% equ 0 goto :is_admin

echo [INFO] Dang yeu cau quyen Administrator...
powershell -NoProfile -ExecutionPolicy Bypass -Command "try { Start-Process -FilePath '%~f0' -WorkingDirectory '%~dp0' -Verb RunAs } catch { exit 1 }"
if %errorLevel% neq 0 (
    echo.
    echo [CANH BAO] Khong the cap quyen Administrator hoac ban da tu choi UAC.
    echo Dang tiep tuc khoi dong o che do Standard User...
    echo.
    timeout /t 2 >nul
    goto :is_admin
)
exit /b

:is_admin
echo =======================================================
echo   SOP AUTO-LOGGING - RUNNING AS ADMINISTRATOR
echo =======================================================
echo.

:: 3. Kiem tra Python tren may
set "PY_CMD="
python --version >nul 2>&1 && set "PY_CMD=python"
if not defined PY_CMD (
    py -3 --version >nul 2>&1 && set "PY_CMD=py -3"
)
if not defined PY_CMD (
    for %%v in (314 313 312 311 310) do (
        if not defined PY_CMD (
            if exist "%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe" set PY_CMD="%LOCALAPPDATA%\Programs\Python\Python%%v\python.exe"
        )
        if not defined PY_CMD (
            if exist "C:\Program Files\Python%%v\python.exe" set PY_CMD="C:\Program Files\Python%%v\python.exe"
        )
    )
)

if not defined PY_CMD (
    echo [LOI] Khong tim thay Python tren may tinh!
    echo Vui long cai dat Python 3.10 tro len tai: https://www.python.org/
    echo Nho tich chon vao o "Add Python to PATH" khi cai dat.
    echo.
    pause
    exit /b
)

:: 4. Tu dong kiem tra va cai dat thu vien neu chua co (chi mat 5 giay)
%PY_CMD% -c "import pyautogui, PIL" >nul 2>&1
if %errorLevel% neq 0 (
    echo.
    echo [INFO] Phat hien lan dau chay - Dang tu dong cai dat thu vien pyautogui, Pillow...
    %PY_CMD% -m pip install -r auto_logging/requirements.txt
    echo [OK] Cai dat hoan tat!
    echo.
)

:: 5. Chay SOP Auto-Logging
echo Dang khoi dong SOP Auto-Logging HUD...
echo.
%PY_CMD% sop_main.py %*
if %errorLevel% neq 0 (
    echo.
    echo [THONG BAO] Chuong trinh da dung lai voi ma loi: %errorLevel%
    pause
)
