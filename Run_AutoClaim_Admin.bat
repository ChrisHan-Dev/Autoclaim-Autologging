@echo off
title AutoClaim Teleops
cd /d "%~dp0"

:: Check for Administrator privileges
net session >nul 2>&1
if %errorLevel% equ 0 (
    echo =======================================================
    echo   AUTOCLAIM TELEOPS - RUNNING AS ADMINISTRATOR
    echo =======================================================
) else (
    echo =======================================================
    echo   AUTOCLAIM TELEOPS - RUNNING AS STANDARD USER
    echo =======================================================
    echo [TIP] To run with full Admin rights, right-click this file and choose "Run as administrator".
)
echo.

:: Detect Python
set "PY_CMD="
python --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"

if not defined PY_CMD (
    py -3 --version >nul 2>&1
    if not errorlevel 1 set "PY_CMD=py -3"
)

if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python314\python.exe"
if not defined PY_CMD if exist "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" set "PY_CMD=%LOCALAPPDATA%\Programs\Python\Python310\python.exe"

if not defined PY_CMD if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe" set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python311\python.exe"
if not defined PY_CMD if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe" set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python312\python.exe"
if not defined PY_CMD if exist "%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe" set "PY_CMD=%USERPROFILE%\AppData\Local\Programs\Python\Python313\python.exe"

if not defined PY_CMD if exist "C:\Program Files\Python311\python.exe" set "PY_CMD=C:\Program Files\Python311\python.exe"
if not defined PY_CMD if exist "C:\Program Files\Python312\python.exe" set "PY_CMD=C:\Program Files\Python312\python.exe"
if not defined PY_CMD if exist "C:\Program Files\Python313\python.exe" set "PY_CMD=C:\Program Files\Python313\python.exe"

if not defined PY_CMD (
    echo =======================================================
    echo   [ERROR] Python was not found on this computer!
    echo =======================================================
    echo Please install Python 3.10 or newer from: https://www.python.org/
    echo Remember to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:: Check and install dependencies if missing
"%PY_CMD%" -c "import easyocr" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Auto-Claim dependencies not found. Installing automatically...
    "%PY_CMD%" -m pip install -r auto_claim/requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies. Please check your internet connection.
        pause
        exit /b 1
    )
    echo [OK] Installation complete!
    echo.
)

:: Launch Auto-Claim
echo Starting AutoClaim Teleops GUI...
echo.
"%PY_CMD%" main.py %*
set "EXIT_CODE=%errorLevel%"

if %EXIT_CODE% neq 0 (
    echo.
    echo [NOTICE] Application terminated with exit code: %EXIT_CODE%
    pause
)
