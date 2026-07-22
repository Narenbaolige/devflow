#!/bin/bash
# =============================================================================
# DevFlow 一键启动脚本
#
# 用法：
#   bash start.sh          # 启动后端 + 前端
#   bash start.sh backend  # 仅启动后端
#   bash start.sh frontend # 仅启动前端
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info()  { echo -e "${GREEN}[INFO]${NC}  $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC}  $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ------------------------------------------------------------------
# 环境检查
# ------------------------------------------------------------------
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        log_error "Docker 未运行。请启动 Docker Desktop 后重试。"
        exit 1
    fi
    log_info "Docker ✓"
}

check_python() {
    if ! python --version > /dev/null 2>&1; then
        log_error "Python 未安装。请安装 Python 3.11+ 后重试。"
        exit 1
    fi
    log_info "Python ✓"
}

check_env() {
    if [ ! -f .env ]; then
        log_warn ".env 文件不存在，正在从 .env.example 复制..."
        cp .env.example .env
        log_info "请编辑 .env 文件，填入 API Key 后重新运行。"
        exit 0
    fi
}

# ------------------------------------------------------------------
# 安装依赖
# ------------------------------------------------------------------
install_deps() {
    log_info "安装 Python 依赖..."
    pip install -q -e ".[dev]" 2>&1 | tail -1
    log_info "Python 依赖 ✓"
}

# ------------------------------------------------------------------
# 启动
# ------------------------------------------------------------------
start_backend() {
    log_info "启动 FastAPI 后端 (http://localhost:8000)..."
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

start_frontend() {
    if [ -d frontend ] && [ -f frontend/package.json ]; then
        log_info "启动 React 前端 (http://localhost:5173)..."
        cd frontend
        npm install --silent 2>&1 | tail -1
        npm run dev
    else
        log_warn "前端项目尚未初始化，跳过。"
    fi
}

# ------------------------------------------------------------------
# 主入口
# ------------------------------------------------------------------
case "${1:-all}" in
    backend)
        check_python
        check_env
        install_deps
        start_backend
        ;;
    frontend)
        start_frontend
        ;;
    all)
        check_python
        check_docker
        check_env
        install_deps

        # 后台启动后端
        log_info "启动后端..."
        uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
        BACKEND_PID=$!
        sleep 2

        # 启动前端
        start_frontend

        # 等待
        wait $BACKEND_PID
        ;;
    *)
        echo "用法: bash start.sh [backend|frontend|all]"
        exit 1
        ;;
esac
