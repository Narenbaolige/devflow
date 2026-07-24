"""
沙箱执行引擎模块（C 负责）。

默认使用本地沙箱（零依赖），通过 SANDBOX_MODE=docker 切换到 Docker 加固模式。
接口统一：create_sandbox() 返回 BaseSandbox 实例。

核心设计：
  - execute(command, cwd, timeout) → CommandResult — 沙箱唯一原语
  - 沙箱不解析输出、不判断语言、不决策下一步
  - Agent 自行决定跑什么命令、如何解读结果

Usage:
    from app.sandbox import create_sandbox

    sandbox = create_sandbox()
    r = sandbox.execute("git clone --depth 1 --branch main URL repo")
    r = sandbox.execute("python -m pytest -v", cwd="repo")
"""

import os

from app.sandbox.base import BaseSandbox, CommandResult


def create_sandbox() -> BaseSandbox:
    """
    创建沙箱实例。

    根据 SANDBOX_MODE 环境变量选择实现：
      - local（默认）：LocalSandbox — 本机 subprocess 执行，零额外依赖
      - docker：       DockerSandbox — Docker 容器隔离，需要 Docker Desktop

    Usage:
        sandbox = create_sandbox()
        r = sandbox.execute("echo hello")
        print(r.stdout)
    """
    mode = os.getenv("SANDBOX_MODE", "local").lower()

    if mode == "docker":
        from app.sandbox.docker import DockerSandbox
        return DockerSandbox()
    else:
        from app.sandbox.local import LocalSandbox
        return LocalSandbox()


__all__ = ["BaseSandbox", "CommandResult", "create_sandbox"]
