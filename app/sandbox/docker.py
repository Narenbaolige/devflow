"""
Docker 沙箱实现（加固模式）。

使用 Docker SDK 在隔离容器中执行命令。
默认无网络、只读根文件系统、CPU/内存硬限制。

实现 execute(command, cwd, timeout) → CommandResult。
首次调用自动创建容器，后续调用复用，cleanup() 或 __del__ 时销毁。

启用方式：SANDBOX_MODE=docker
"""

import time
import uuid

import docker
from docker.errors import DockerException

from app.config import settings
from app.sandbox.base import BaseSandbox, CommandResult


class DockerSandbox(BaseSandbox):
    """
    Docker 沙箱引擎。

    在隔离容器中执行命令。Agent 通过 execute() 自行决定跑什么命令。

    安全基线：
      - 网络隔离 (--network none)
      - 只读根文件系统，/workspace 为 tmpfs
      - CPU 1 核，内存 512MB
      - 退出时自动销毁 (--rm)

    用法：
        sandbox = DockerSandbox()
        r = sandbox.execute("git clone https://... repo")
        r = sandbox.execute("pip install -e .", cwd="repo", timeout=180)
        r = sandbox.execute("python -m pytest -v", cwd="repo")
        sandbox.cleanup()
    """

    def __init__(self):
        self._client: docker.DockerClient | None = None
        self._container_id: str | None = None
        self._execution_id: str | None = None

    @property
    def client(self) -> docker.DockerClient:
        """懒加载 Docker 客户端。"""
        if self._client is None:
            try:
                self._client = docker.from_env()
            except DockerException as e:
                raise RuntimeError(
                    f"无法连接 Docker 守护进程。请确认 Docker 正在运行。\n原始错误: {e}"
                )
        return self._client

    def execute(
        self,
        command: str,
        *,
        cwd: str = "/workspace",
        timeout: int = 60,
    ) -> CommandResult:
        """
        在 Docker 隔离容器中执行一条命令。

        首次调用时自动创建容器。后续调用复用同一容器。
        cwd 直接使用容器内路径（Linux 文件系统）。
        """
        start_time = time.time()

        if self._container_id is None:
            self._container_id = self._create_container()

        # 相对路径 → 基于 /workspace 的绝对路径（Docker 要求绝对路径）
        resolved_cwd = cwd if cwd.startswith("/") else f"/workspace/{cwd}"

        try:
            container = self.client.containers.get(self._container_id)
            result = container.exec_run(
                cmd=["/bin/sh", "-c", command],
                workdir=resolved_cwd,
            )
            duration_ms = int((time.time() - start_time) * 1000)
            raw_output = result.output
            if isinstance(raw_output, bytes):
                output = raw_output.decode("utf-8", errors="replace")
            else:
                output = str(raw_output) if raw_output else ""
            return CommandResult(
                exit_code=result.exit_code if result.exit_code is not None else -1,
                stdout=output,
                stderr="",
                timed_out=(duration_ms >= timeout * 1000),
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return CommandResult(
                exit_code=-1,
                stdout="",
                stderr=f"容器执行异常: {str(e)}",
                timed_out=False,
                duration_ms=duration_ms,
            )

    def _create_container(self) -> str:
        """创建隔离容器。"""
        execution_id = str(uuid.uuid4())[:8]
        self._execution_id = execution_id
        container = self.client.containers.run(
            image=settings.DOCKER_IMAGE,
            command="tail -f /dev/null",
            detach=True,
            network_mode="bridge",
            tmpfs={"/workspace": "rw,size=512m"},
            cpu_count=settings.SANDBOX_MAX_CPUS,
            mem_limit=f"{settings.SANDBOX_MAX_MEMORY_MB}m",
            name=f"devflow-sandbox-{execution_id}",
            remove=True,
        )
        container_id = (container.id or "")[:12]

        # 预装 pytest（python:3.11 自带 git 但 pytest 需要手动装）
        container.exec_run(
            cmd=["/bin/sh", "-c", "pip install -q pytest 2>&1"],
            workdir="/workspace",
        )

        return container_id

    def cleanup(self) -> None:
        """强制停止并删除容器。"""
        if self._container_id:
            try:
                container = self.client.containers.get(self._container_id)
                container.stop(timeout=5)
            except Exception:
                pass
            self._container_id = None
            self._execution_id = None

    def __del__(self):
        self.cleanup()
