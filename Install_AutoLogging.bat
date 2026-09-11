@echo off
title Install SOP Auto-Logging Dependencies
cd /d "%~dp0"

echo =======================================================
echo   INSTALLING DEPENDENCIES FOR SOP AUTO-LOGGING
echo =======================================================
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

echo [1/2] Checking Python version...
"%PY_CMD%" --version
echo.

echo [2/2] Installing lightweight dependencies: pyautogui, Pillow...
"%PY_CMD%" -m pip install -r auto_logging/requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] An error occurred during installation.
    echo Please check your internet connection and try again.
    echo.
    pause
    exit /b 1
)

echo.
echo =======================================================
echo   [SUCCESS] INSTALLATION COMPLETED!
echo =======================================================
echo You can now use SOP Auto-Logging:
echo   - Double-click: Run_SOP_Admin.bat to start.
echo.

pause
