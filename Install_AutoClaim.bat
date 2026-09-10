@echo off
title Cai dat Auto-Claim Teleops
cd /d "%~dp0"

echo =======================================================
echo   CAI DAT THU VIEN CHO AUTO-CLAIM (OCR & VISION)
echo =======================================================
echo.

:: Kiem tra Python
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo [LOI] Khong tim thay Python tren may tinh cua ban!
    echo Vui long cai dat Python 3.10 tro len tai: https://www.python.org/
    echo LUU Y: Nho tich chon vao o "Add Python to PATH" khi cai dat.
    echo.
    pause
    exit /b
)

echo [1/2] Kiem tra phien ban Python...
python --version
echo.

echo [2/2] Dang cai dat thu vien Auto-Claim (EasyOCR, OpenCV, MSS, numpy...)...
echo (Qua trinh nay co the mat 1-3 phut tuy toc do mang)...
python -m pip install -r auto_claim/requirements.txt

if %errorLevel% equ 0 (
    echo.
    echo =======================================================
    echo   [THANH CONG] CAI DAT AUTO-CLAIM HOAN TAT!
    echo =======================================================
    echo Ban da co the su dung ngay:
    echo   - Click dup vao: Run_AutoClaim_Admin.bat de mo tool.
    echo.
) else (
    echo.
    echo [LOI] Co van de xay ra trong qua trinh cai dat.
    echo.
)

pause
