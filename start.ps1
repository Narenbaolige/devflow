# DevFlow — Windows 一键启动 (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DevFlow — Multi-Agent Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── 后端 ──
Write-Host "[1/2] Starting backend (port 8000)..." -ForegroundColor Yellow
$backendCmd = "cd '$root'; .\.venv312\Scripts\python.exe -m app.run"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "       Backend  launched in new window." -ForegroundColor Green

# ── 前端 ──
Write-Host "[2/2] Starting frontend (port 5173)..." -ForegroundColor Yellow
if (Test-Path "$root\frontend\node_modules") {
    # Use npm.cmd so this also works when PowerShell's script execution policy
    # blocks the npm.ps1 shim.
    $frontendCmd = "cd '$root\frontend'; npm.cmd run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "       Frontend launched in new window." -ForegroundColor Green
} else {
    Write-Host "       Frontend node_modules not found. Run: cd frontend; npm install" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the terminal windows or press Ctrl+C in each to stop." -ForegroundColor Gray
Read-Host "Press Enter to close this window"
