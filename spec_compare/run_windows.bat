@echo off
setlocal
cd /d "%~dp0"

if not exist "src\main.py" (
    echo.
    echo ERROR: src\main.py not found. Place this BAT next to the src folder.
    echo.
    pause
    exit /b 1
)

echo ========================================================
echo   SpecCompare - build Windows EXE
echo ========================================================
echo.

echo [1/3] Checking Python...
set "PY_CMD="

py --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=py"

if defined PY_CMD goto py_found

python --version >nul 2>&1
if not errorlevel 1 set "PY_CMD=python"

:py_found
if not defined PY_CMD (
    echo.
    echo ERROR: Python not found. Install from https://www.python.org/downloads/
    echo and enable "Add python.exe to PATH" during setup.
    echo.
    pause
    exit /b 1
)

echo [OK] Using: %PY_CMD%

echo [2/3] Installing dependencies...
%PY_CMD% -m pip install --upgrade pip
%PY_CMD% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo.
    echo ERROR: pip install failed.
    pause
    exit /b 1
)

echo.
echo [3/3] Running PyInstaller - this may take several minutes...
%PY_CMD% -m PyInstaller --onefile --windowed --name SpecCompare --paths src --collect-all rapidfuzz src\main.py

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   DONE. Open dist\SpecCompare.exe
echo ========================================================
pause
