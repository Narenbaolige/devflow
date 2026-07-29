@echo off
setlocal

set ROOT=%~dp0

echo ========================================
echo   DevFlow - Multi-Agent Platform
echo ========================================
echo.

set PYTHON=
if exist "%ROOT%.venv\Scripts\python.exe" (
    set PYTHON=%ROOT%.venv\Scripts\python.exe
    echo [OK] Found .venv
) else if exist "%ROOT%.venv312\Scripts\python.exe" (
    set PYTHON=%ROOT%.venv312\Scripts\python.exe
    echo [OK] Found .venv312
)

if "%PYTHON%"=="" (
    echo [ERR] No virtual environment found. Run: python -m venv .venv
    pause
    exit /b 1
)

if exist "%ROOT%frontend\node_modules" (
    echo [OK] Found node_modules
) else (
    echo [WARN] frontend dependencies not installed.
    echo       Run: cd frontend ^& npm install
    echo.
)

echo [1/2] Starting backend (port 8000)...
start "DevFlow Backend" cmd /k "cd /d %ROOT% && %PYTHON% -m app.run"
echo       Backend launched in new window.

echo [2/2] Starting frontend (port 5173)...
if exist "%ROOT%frontend\node_modules" (
    start "DevFlow Frontend" cmd /k "cd /d %ROOT%frontend && npm.cmd run dev"
    echo       Frontend launched in new window.
) else (
    echo       Skipped - install dependencies first.
)

echo.
echo ========================================
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo ========================================
echo.
echo Close each terminal window to stop.
pause
