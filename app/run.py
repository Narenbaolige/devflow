"""DevFlow 启动入口。

Windows + AsyncPostgresSaver 需要 SelectorEventLoop。直接使用 ``uvicorn`` CLI
的非 reload 模式会选用 ProactorEventLoop，因此 Windows 部署应通过本模块启动。
"""

import asyncio
import sys

import uvicorn
from dotenv import load_dotenv

# 必须在导入 settings 前加载 .env；否则会退回 memory Checkpointer。
# 不覆盖终端已设置的 PORT 等运行时参数。
load_dotenv()
from app.config import settings


def main() -> None:
    """以与 psycopg 异步驱动兼容的事件循环启动 API。"""
    config = uvicorn.Config("app.main:app", host=settings.HOST, port=settings.PORT)
    server = uvicorn.Server(config)

    if sys.platform == "win32":
        with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
            runner.run(server.serve())
    else:
        asyncio.run(server.serve())


if __name__ == "__main__":
    main()
