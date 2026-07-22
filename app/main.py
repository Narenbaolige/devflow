"""
FastAPI 应用入口。

启动方式：
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(override=True)

from app.api.tasks import router as tasks_router  # noqa: E402
from app.config import settings  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。"""
    # 启动时
    print(f"[DevFlow] 启动完成 — {settings.HOST}:{settings.PORT}")
    yield
    # 关闭时
    print("[DevFlow] 正在关闭...")


app = FastAPI(
    title="DevFlow API",
    description="Multi-Agent Collaborative Intelligent Agent for Software Engineering",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — 允许前端开发服务器跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(tasks_router, prefix="/tasks", tags=["tasks"])


@app.get("/health")
async def health_check():
    """健康检查端点。"""
    return {"status": "ok", "version": "0.1.0", "service": "devflow-api"}
