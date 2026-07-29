# DevFlow — Windows 一键启动 (PowerShell)
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DevFlow — Multi-Agent Platform" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$root = Split-Path -Parent $MyInvocation.MyCommand.Path

# ── Python 检测：优先 .venv，回退到系统 python ──
$python = $null
if (Test-Path "$root\.venv\Scripts\python.exe") {
    $python = "$root\.venv\Scripts\python.exe"
    Write-Host "[ OK ] Found .venv" -ForegroundColor Green
} elseif (Test-Path "$root\.venv312\Scripts\python.exe") {
    $python = "$root\.venv312\Scripts\python.exe"
    Write-Host "[ OK ] Found .venv312" -ForegroundColor Green
} else {
    $sysPython = (Get-Command python -ErrorAction SilentlyContinue).Source
    if ($sysPython) {
        $python = $sysPython
        Write-Host "[ !! ] No virtual environment found, using system python: $python" -ForegroundColor Yellow
        Write-Host "       Consider: python -m venv .venv; .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "[ ERR ] Python not found. Install Python 3.11+ and create a venv." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ── npm 检测 ──
$npm = $null
if (Test-Path "$root\frontend\node_modules\.package-lock.json") {
    $npmExe = (Get-Command npm.cmd -ErrorAction SilentlyContinue).Source
    if (-not $npmExe) { $npmExe = (Get-Command npm -ErrorAction SilentlyContinue).Source }
    if ($npmExe) {
        $npm = $npmExe
        Write-Host "[ OK ] Found node_modules + npm" -ForegroundColor Green
    } else {
        Write-Host "[ ERR ] npm not found. Please install Node.js 18+" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "[ !! ] frontend dependencies not installed" -ForegroundColor Yellow
    Write-Host "       Run: cd frontend; npm install" -ForegroundColor Yellow
    Write-Host ""
}

# ── 后端 ──
Write-Host "[1/2] Starting backend (port 8000)..." -ForegroundColor Yellow
$backendCmd = "cd '$root'; & '$python' -m app.run"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
Write-Host "       Backend launched in new window." -ForegroundColor Green

# ── 前端 ──
if ($npm) {
    Write-Host "[2/2] Starting frontend (port 5173)..." -ForegroundColor Yellow
    $frontendCmd = "cd '$root\frontend'; & '$npm' run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
    Write-Host "       Frontend launched in new window." -ForegroundColor Green
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Backend:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Close the terminal windows or press Ctrl+C in each to stop." -ForegroundColor Gray
Read-Host "Press Enter to close this window"
