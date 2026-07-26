"""LangGraph Checkpointer 生命周期管理。

开发默认使用内存；部署时设置 CHECKPOINTER_BACKEND=postgres，任务状态即可跨
进程恢复。这里保持可选导入，避免本地开发在未安装 PostgreSQL 驱动时无法启动。
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from langgraph.checkpoint.memory import MemorySaver

from app.config import settings


@asynccontextmanager
async def managed_checkpointer() -> AsyncIterator[object]:
    """按配置创建并在应用关闭时释放 Checkpointer。"""
    if settings.CHECKPOINTER_BACKEND == "memory":
        yield MemorySaver()
        return

    if settings.CHECKPOINTER_BACKEND != "postgres":
        raise RuntimeError("CHECKPOINTER_BACKEND 仅支持 memory 或 postgres")

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ImportError as exc:
        raise RuntimeError(
            "PostgreSQL Checkpointer 未安装；请执行 pip install -e '.[dev]'"
        ) from exc

    async with AsyncPostgresSaver.from_conn_string(settings.CHECKPOINTER_DATABASE_URL) as saver:
        await saver.setup()
        yield saver
