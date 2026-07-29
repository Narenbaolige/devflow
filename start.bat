@echo off
chcp 65001 >nul
echo ========================================
echo   DevFlow — Multi-Agent Platform
echo ========================================
echo.

REM ── 后端 ──
echo [1/2] Starting backend (port 8000)...
start "DevFlow Backend" cmd /k "cd /d %~dp0 && .venv312\Scripts\python.exe -m app.run"
echo          Backend  launched in new window.

REM ── 前端 ──
echo [2/2] Starting frontend (port 5173)...
if exist "%~dp0frontend\node_modules" (
    start "DevFlow Frontend" cmd /k "cd /d %~dp0frontend && npm.cmd run dev"
    echo          Frontend launched in new window.
) else (
    echo          Frontend dependencies not installed. Install them first:
    echo            cd frontend ^&^& npm install
)

echo.
echo ========================================
echo   Backend:  http://localhost:8000/docs
echo   Frontend: http://localhost:5173
echo ========================================
echo.
echo Close the terminal windows or press Ctrl+C in each to stop.
pause
