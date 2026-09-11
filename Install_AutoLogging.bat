@echo off
title Cai dat SOP Auto-Logging (5 Giay)
cd /d "%~dp0"

echo =======================================================
echo   CAI DAT THU VIEN CHO SOP AUTO-LOGGING (SIEU TOC)
echo =======================================================
echo.

:: 1. Tu dong tim va them duong dan Python vao PATH
for %%v in (314 313 312 311 310) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%v" (
        set "PATH=%LOCALAPPDATA%\Programs\Python\Python%%v;%LOCALAPPDATA%\Programs\Python\Python%%v\Scripts;%PATH%"
    )
    if exist "C:\Program Files\Python%%v" (
        set "PATH=C:\Program Files\Python%%v;C:\Program Files\Python%%v\Scripts;%PATH%"
    )
)

:: 2. Kiem tra Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [THONG BAO] May tinh chua co Python!
    echo Dang thu tu dong tai va cai dat Python 3.12 qua Windows Winget...
    winget install Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements
    
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python312;%LOCALAPPDATA%\Programs\Python\Python312\Scripts;C:\Program Files\Python312;C:\Program Files\Python312\Scripts;%PATH%"
    
    python --version >nul 2>&1
    if %errorLevel% neq 0 (
        echo.
        echo [LOI] Khong the tu dong cai dat Python tren may nay.
        echo Ban chi can cai dat Python 1 lan duy nhat:
        echo   1. Truy cap: https://www.python.org/downloads/
        echo   2. Tai Python va mo file cai dat.
        echo   3. [QUAN TRONG]: Tich vao o "Add Python to PATH".
        echo   4. Cai xong, click dup lai file nay!
        echo.
        pause
        exit /b
    )
    echo [OK] Da cai dat Python thanh cong!
    echo.
)

echo [1/2] Kiem tra phien ban Python...
python --version
echo.

echo [2/2] Dang cai dat thu vien nhe (pyautogui, Pillow)...
python -m pip install -r auto_logging/requirements.txt

if %errorLevel% equ 0 (
    echo.
    echo =======================================================
    echo   [THANH CONG] CAI DAT HOAN TAT TRONG TICH TAC!
    echo =======================================================
    echo Ban da co the su dung ngay SOP Auto-Logging:
    echo   - Click dup vao: Run_SOP_Admin.bat de bat dau dung.
    echo.
) else (
    echo.
    echo [LOI] Co van de xay ra trong qua trinh cai dat.
    echo Vui long kiem tra ket noi mang va thu lai.
    echo.
)

pause
