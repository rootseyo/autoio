@echo off
setlocal

where py >nul 2>nul
if %errorlevel% equ 0 (
    set "PYTHON_CMD=py -3"
) else (
    set "PYTHON_CMD=python"
)

echo [1/3] Preparing build tools...
%PYTHON_CMD% -m pip install --upgrade pip
if %errorlevel% neq 0 goto :error
%PYTHON_CMD% -m pip install -e ".[build]"
if %errorlevel% neq 0 goto :error

echo [2/3] Running tests...
%PYTHON_CMD% -m unittest discover -s tests -v
if %errorlevel% neq 0 goto :error

echo [3/3] Building AutoIO-Windows.exe...
%PYTHON_CMD% -m PyInstaller --clean --noconfirm --onefile --windowed --collect-all customtkinter --icon "assets\autoio.ico" --name "AutoIO-Windows" auto_kb_mouse.py
if %errorlevel% neq 0 goto :error

echo Build complete: dist\AutoIO-Windows.exe
exit /b 0

:error
echo Build failed with exit code %errorlevel%.
exit /b %errorlevel%
